/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //Hub 的 HTTP 入口，提供 POST /send 与 POST /disconnect
 * @File: http.go
 * @Time: 2026/10/23 10:39:00
 * @All Rights Reserve By Brtc
 */

// Package server 提供 API 调用的 HTTP 转发入口。
package server

import (
	"bytes"
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"hub/config"
	"hub/internal/agent"
)

const (
	maxBodyBytes         = 1 << 20
	gatewayReadyTimeout  = 2 * time.Second
	gatewayReadyInterval = 50 * time.Millisecond
)

// Server 是 Hub 的 HTTP 服务。
type Server struct {
	cfg    *config.Config
	logger *slog.Logger
	pool   *agent.Pool
	http   *http.Server
}

type sendRequest struct {
	AgentID    string `json:"agent_id"`
	BotID      string `json:"bot_id"`
	GatewayURL string `json:"gateway_url"`
	GatewayKey string `json:"gateway_key"`
	AccountID  string `json:"account_id"`
	ThreadID   string `json:"thread_id"`
	PeerID     string `json:"peer_id"`
	Text       string `json:"text"`
}

type disconnectRequest struct {
	AgentID string `json:"agent_id"`
}

type textBody struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type businessEnvelope struct {
	Type       string   `json:"type"`
	AccountID  string   `json:"account_id"`
	ThreadID   string   `json:"thread_id"`
	FromDevice string   `json:"from_device"`
	Data       textBody `json:"data"`
}

type outboundFrame struct {
	To   string           `json:"to"`
	Data businessEnvelope `json:"data"`
}

type statusBody struct {
	OK    bool   `json:"ok"`
	Error string `json:"error,omitempty"`
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: New(cfg *config.Config, logger *slog.Logger, pool *agent.Pool)
 * @Description //创建绑定 POST /send、POST /disconnect 和 GET /healthz 的 HTTP 服务
 * @Date :2026/10/23 10:39:00
 * @Param: cfg 运行配置；logger 日志；pool 上游连接池
 * @return: *Server
 */
func New(cfg *config.Config, logger *slog.Logger, pool *agent.Pool) *Server {
	srv := &Server{
		cfg:    cfg,
		logger: logger,
		pool:   pool,
	}
	mux := http.NewServeMux()
	mux.HandleFunc("POST /send", srv.handleSend)
	mux.HandleFunc("POST /disconnect", srv.handleDisconnect)
	mux.HandleFunc("GET /healthz", srv.handleHealth)
	srv.http = &http.Server{
		Addr:              cfg.HTTPAddr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	return srv
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Server) Start()
 * @Description //启动 HTTP 监听，正常关闭时不返回错误
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 监听失败时返回 error
 */
func (s *Server) Start() error {
	s.logger.Info("hub http listening", slog.String("addr", s.http.Addr))
	err := s.http.ListenAndServe()
	if err != nil && !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("listen and serve: %w", err)
	}
	return nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Server) Shutdown(ctx context.Context)
 * @Description //停止接受新的 HTTP 请求并等待在途请求结束
 * @Date :2026/10/23 10:39:00
 * @Param: ctx 关闭超时上下文
 * @return: 关闭失败时返回 error
 */
func (s *Server) Shutdown(ctx context.Context) error {
	if err := s.http.Shutdown(ctx); err != nil {
		return fmt.Errorf("shutdown http: %w", err)
	}
	return nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Server) handleSend(w http.ResponseWriter, r *http.Request)
 * @Description //校验请求、懒取连接；未连通时最多等 2 秒再下发上行信封
 * @Date :2026/10/23 10:39:00
 * @Param: w 响应写入器；r HTTP 请求
 * @return: 无
 */
func (s *Server) handleSend(w http.ResponseWriter, r *http.Request) {
	if !s.authorized(r) {
		s.logger.Warn("rejected send, internal token mismatch", slog.String("remote", r.RemoteAddr))
		writeJSON(w, http.StatusUnauthorized, statusBody{OK: false, Error: "unauthorized"})
		return
	}

	var req sendRequest
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := decoder.Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, statusBody{OK: false, Error: "invalid request body"})
		return
	}
	normalizeSend(&req)
	if message := validateSend(req); message != "" {
		writeJSON(w, http.StatusBadRequest, statusBody{OK: false, Error: message})
		return
	}

	payload, err := buildEnvelope(req)
	if err != nil {
		s.logger.Error("marshal outbound frame failed", slog.Any("err", err))
		writeJSON(w, http.StatusInternalServerError, statusBody{OK: false, Error: "marshal outbound frame failed"})
		return
	}

	conn := s.pool.Get(agent.ConnConfig{
		AgentID:    req.AgentID,
		BotID:      req.BotID,
		PeerID:     req.PeerID,
		GatewayURL: req.GatewayURL,
		GatewayKey: req.GatewayKey,
	})
	if err := s.sendWhenReady(r.Context(), conn, payload); err != nil {
		status := http.StatusBadGateway
		if errors.Is(err, agent.ErrNotConnected) {
			status = http.StatusServiceUnavailable
		}
		s.logger.Warn(
			"send to gateway failed",
			slog.String("agent_id", req.AgentID),
			slog.String("bot_id", req.BotID),
			slog.Any("err", err),
		)
		writeJSON(w, status, statusBody{OK: false, Error: err.Error()})
		return
	}

	s.logger.Info(
		"send accepted",
		slog.String("agent_id", req.AgentID),
		slog.String("bot_id", req.BotID),
		slog.Int("bytes", len(payload)),
	)
	writeJSON(w, http.StatusOK, statusBody{OK: true})
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Server) sendWhenReady(ctx context.Context, conn *agent.Conn, payload []byte)
 * @Description //连接未就绪时沿用 Get 已启动的 supervisor 建连，最多等 2 秒，每 50 毫秒重试一次下发
 * @Date :2026/10/24 09:48:00
 * @Param: ctx 请求上下文，取消时停止等待；conn 上游连接，Get 在连接不存在时已经调用 Start；payload 要下发的 JSON
 * @return: 下发成功返回 nil；超时仍未连通返回 ErrNotConnected；其它写失败原样返回
 */
func (s *Server) sendWhenReady(ctx context.Context, conn *agent.Conn, payload []byte) error {
	deadline := time.Now().Add(gatewayReadyTimeout)
	for {
		err := conn.Send(payload)
		if !errors.Is(err, agent.ErrNotConnected) {
			return err
		}
		remain := time.Until(deadline)
		if ctx.Err() != nil || remain <= 0 {
			return err
		}
		wait := gatewayReadyInterval
		if wait > remain {
			wait = remain
		}
		timer := time.NewTimer(wait)
		select {
		case <-ctx.Done():
			timer.Stop()
			return err
		case <-timer.C:
		}
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Server) handleDisconnect(w http.ResponseWriter, r *http.Request)
 * @Description //校验内部令牌后，按 agent_id 从连接池移除并关闭上游 WebSocket
 * @Date :2026/10/26 22:43:00
 * @Param: w 响应写入器；r HTTP 请求，body 为 {"agent_id":"..."}
 * @return: 无
 */
func (s *Server) handleDisconnect(w http.ResponseWriter, r *http.Request) {
	if !s.authorized(r) {
		s.logger.Warn("rejected disconnect, internal token mismatch", slog.String("remote", r.RemoteAddr))
		writeJSON(w, http.StatusUnauthorized, statusBody{OK: false, Error: "unauthorized"})
		return
	}

	var req disconnectRequest
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	if err := decoder.Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, statusBody{OK: false, Error: "invalid request body"})
		return
	}
	req.AgentID = strings.TrimSpace(req.AgentID)
	if req.AgentID == "" {
		writeJSON(w, http.StatusBadRequest, statusBody{OK: false, Error: "agent_id is required"})
		return
	}

	if !s.pool.Remove(req.AgentID) {
		s.logger.Info("disconnect agent not connected", slog.String("agent_id", req.AgentID))
		writeJSON(w, http.StatusNotFound, statusBody{OK: false, Error: "agent not connected"})
		return
	}

	s.logger.Info("disconnect accepted", slog.String("agent_id", req.AgentID))
	writeJSON(w, http.StatusOK, statusBody{OK: true})
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Server) handleHealth(w http.ResponseWriter, r *http.Request)
 * @Description //返回进程存活探针，不检查上游连接
 * @Date :2026/10/23 10:39:00
 * @Param: w 响应写入器；r HTTP 请求，未使用
 * @return: 无
 */
func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok"))
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Server) authorized(r *http.Request)
 * @Description //在配置了 INTERNAL_TOKEN 时校验 X-Internal-Token
 * @Date :2026/10/23 10:39:00
 * @Param: r HTTP 请求
 * @return: 未配置令牌或令牌匹配时返回 true
 */
func (s *Server) authorized(r *http.Request) bool {
	want := s.cfg.InternalToken
	if want == "" {
		return true
	}
	got := r.Header.Get("X-Internal-Token")
	if len(got) != len(want) {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(got), []byte(want)) == 1
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: normalizeSend(req *sendRequest)
 * @Description //去掉路由字段首尾空白，正文保持原样
 * @Date :2026/10/23 10:39:00
 * @Param: req 待整理的请求
 * @return: 无
 */
func normalizeSend(req *sendRequest) {
	req.AgentID = strings.TrimSpace(req.AgentID)
	req.BotID = strings.TrimSpace(req.BotID)
	req.GatewayURL = strings.TrimSpace(req.GatewayURL)
	req.GatewayKey = strings.TrimSpace(req.GatewayKey)
	req.AccountID = strings.TrimSpace(req.AccountID)
	req.ThreadID = strings.TrimSpace(req.ThreadID)
	req.PeerID = strings.TrimSpace(req.PeerID)
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: validateSend(req sendRequest)
 * @Description //检查上行必填字段，正文允许为空
 * @Date :2026/10/23 10:39:00
 * @Param: req 已整理的请求
 * @return: 第一个缺失字段的说明；字段齐全时返回空串
 */
func validateSend(req sendRequest) string {
	switch {
	case req.AgentID == "":
		return "agent_id is required"
	case req.BotID == "":
		return "bot_id is required"
	case req.GatewayURL == "":
		return "gateway_url is required"
	case req.GatewayKey == "":
		return "gateway_key is required"
	case req.AccountID == "":
		return "account_id is required"
	case req.ThreadID == "":
		return "thread_id is required"
	case req.PeerID == "":
		return "peer_id is required"
	default:
		return ""
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: buildEnvelope(req sendRequest)
 * @Description //组装发往 Hermes 的 {to, data} 信封
 * @Date :2026/10/23 10:39:00
 * @Param: req 已校验的发送请求
 * @return: 信封 JSON；编码失败时返回 error
 */
func buildEnvelope(req sendRequest) ([]byte, error) {
	frame := outboundFrame{
		To: req.BotID,
		Data: businessEnvelope{
			Type:       "message",
			AccountID:  req.AccountID,
			ThreadID:   req.ThreadID,
			FromDevice: req.PeerID,
			Data: textBody{
				Type: "message",
				Text: req.Text,
			},
		},
	}
	payload, err := marshalJSON(frame)
	if err != nil {
		return nil, fmt.Errorf("marshal outbound frame: %w", err)
	}
	return payload, nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: marshalJSON(value any)
 * @Description //编码 JSON，且不转义正文里的 HTML 字符
 * @Date :2026/10/23 10:39:00
 * @Param: value 要编码的值
 * @return: 不带尾部换行的 JSON；编码失败时返回 error
 */
func marshalJSON(value any) ([]byte, error) {
	var buf bytes.Buffer
	encoder := json.NewEncoder(&buf)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(value); err != nil {
		return nil, err
	}
	return bytes.TrimRight(buf.Bytes(), "\n"), nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: writeJSON(w http.ResponseWriter, status int, body statusBody)
 * @Description //写出 JSON 响应
 * @Date :2026/10/23 10:39:00
 * @Param: w 响应写入器；status HTTP 状态码；body 响应体
 * @return: 无
 */
func writeJSON(w http.ResponseWriter, status int, body statusBody) {
	payload, err := json.Marshal(body)
	if err != nil {
		http.Error(w, "encode response failed", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write(payload)
}
