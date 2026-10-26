/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //单条到网关的 WebSocket 客户端
 * @File: conn.go
 * @Time: 2026/10/23 10:39:00
 * @All Rights Reserve By Brtc
 */

package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"

	"hub/internal/jwt"
	"hub/internal/model"
)

const (
	heartbeatInterval = 30 * time.Second
	writeWait         = 10 * time.Second
	handshakeTimeout  = 10 * time.Second
	maxFrameBytes     = 1 << 20
)

// ErrNotConnected 表示当前还没有可用的网关连接。
var ErrNotConnected = errors.New("gateway connection is not established")

// FrameHandler 处理一条已经解析的下行帧。raw 是网关上的原始 JSON。
type FrameHandler func(raw []byte, frame model.WSMessage)

// ConnConfig 是一条上游连接的目标网关参数，由 POST /send 带入。
type ConnConfig struct {
	// AgentID 是连接池键。
	AgentID string
	// BotID 是 Hermes 的 ws_session_id，也是上行信封的 to。
	BotID string
	// PeerID 是平台侧智能体对端标识，用作上游连接的 ws_session_id。
	PeerID string
	// GatewayURL 是已含 /ws 的网关地址。
	GatewayURL string
	// GatewayKey 是签发连接 JWT 的 HMAC 密钥。
	GatewayKey string
}

// Conn 是一条到网关的长连接，断线后按原身份重连。
type Conn struct {
	cfg       ConnConfig
	sessionID string
	logger    *slog.Logger
	onFrame   FrameHandler

	ctx    context.Context
	cancel context.CancelFunc

	writeMu sync.Mutex
	ws      *websocket.Conn
	up      atomic.Bool

	started   atomic.Bool
	closeOnce sync.Once
	stopped   chan struct{}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: NewConn(cfg ConnConfig, logger *slog.Logger, onFrame FrameHandler)
 * @Description //创建一条尚未拨号的上游连接，优先使用 peer_id 作为 ws_session_id，为空时回退 hub-<bot_id>
 * @Date :2026/10/23 10:39:00
 * @Param: cfg 网关参数；logger 日志；onFrame 下行帧回调
 * @return: *Conn
 */
func NewConn(cfg ConnConfig, logger *slog.Logger, onFrame FrameHandler) *Conn {
	sessionID := strings.TrimSpace(cfg.PeerID)
	if sessionID == "" {
		sessionID = "hub-" + strings.TrimSpace(cfg.BotID)
	}
	ctx, cancel := context.WithCancel(context.Background())
	conn := &Conn{
		cfg:       cfg,
		sessionID: sessionID,
		logger:    logger.With(
			slog.String("agent_id", cfg.AgentID),
			slog.String("ws_session_id", sessionID),
		),
		onFrame:   onFrame,
		ctx:       ctx,
		cancel:    cancel,
		stopped:   make(chan struct{}),
	}
	if strings.TrimSpace(cfg.PeerID) == "" {
		conn.logger.Warn("peer_id missing, fallback ws_session_id to hub-<bot_id>")
	}
	return conn
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) Start()
 * @Description //启动拨号、读循环、心跳和断线重连，重复调用无效
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 无
 */
func (c *Conn) Start() {
	if !c.started.CompareAndSwap(false, true) {
		return
	}
	c.logger.Info("gateway supervisor started", slog.String("gateway_url", c.cfg.GatewayURL))
	go c.supervise()
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) Close()
 * @Description //取消上下文、关闭套接字并等待全部 goroutine 退出
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 当前实现返回 nil
 */
func (c *Conn) Close() error {
	c.closeOnce.Do(func() {
		c.cancel()
		c.dropConn()
	})
	if c.started.Load() {
		<-c.stopped
	}
	return nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) Send(payload []byte)
 * @Description //把一帧写入当前网关连接；未连通时立即返回，不等待拨号
 * @Date :2026/10/23 10:39:00
 * @Param: payload 要发送的 JSON
 * @return: 未连通时返回 ErrNotConnected，写失败时返回 error
 */
func (c *Conn) Send(payload []byte) error {
	if !c.up.Load() {
		return ErrNotConnected
	}
	c.writeMu.Lock()
	ws := c.ws
	up := c.up.Load()
	c.writeMu.Unlock()
	if !up || ws == nil {
		return ErrNotConnected
	}
	return c.writeMessage(ws, payload)
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) sameGateway(cfg ConnConfig)
 * @Description //判断网关地址、密钥、bot_id 和 peer_id 是否与当前连接一致
 * @Date :2026/10/23 10:39:00
 * @Param: cfg 新的网关参数
 * @return: 四者都相同返回 true
 */
func (c *Conn) sameGateway(cfg ConnConfig) bool {
	return c.cfg.GatewayURL == cfg.GatewayURL &&
		c.cfg.GatewayKey == cfg.GatewayKey &&
		c.cfg.BotID == cfg.BotID &&
		c.cfg.PeerID == cfg.PeerID
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) supervise()
 * @Description //无限重连，退避为 1 秒、2 秒、5 秒，之后封顶 10 秒
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 无
 */
func (c *Conn) supervise() {
	defer close(c.stopped)

	steps := [...]time.Duration{
		time.Second,
		2 * time.Second,
		5 * time.Second,
		10 * time.Second,
	}
	step := 0
	for {
		if c.ctx.Err() != nil {
			return
		}
		established, dialErr := c.dialAndServe()
		if c.ctx.Err() != nil {
			return
		}
		if established {
			step = 0
		}
		delay := steps[step]
		c.logger.Warn(
			"gateway connection lost",
			slog.String("gateway_url", c.cfg.GatewayURL),
			slog.Duration("retry_in", delay),
			slog.Any("err", dialErr),
		)
		if !c.wait(delay) {
			return
		}
		if step < len(steps)-1 {
			step++
		}
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) wait(delay time.Duration)
 * @Description //等待重连间隔，关闭信号到达时提前返回
 * @Date :2026/10/23 10:39:00
 * @Param: delay 等待时长
 * @return: 正常等到时返回 true，连接被关闭时返回 false
 */
func (c *Conn) wait(delay time.Duration) bool {
	timer := time.NewTimer(delay)
	defer timer.Stop()
	select {
	case <-c.ctx.Done():
		return false
	case <-timer.C:
		return true
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) dialAndServe()
 * @Description //拨号成功后一直服务到断线，身份在重连之间保持不变
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: established 表示这次拨号曾经成功；err 是断线或拨号错误
 */
func (c *Conn) dialAndServe() (bool, error) {
	ws, err := c.dial()
	if err != nil {
		return false, err
	}
	if ctxErr := c.ctx.Err(); ctxErr != nil {
		_ = ws.Close()
		return false, fmt.Errorf("dial aborted: %w", ctxErr)
	}

	c.attach(ws)
	defer c.dropConn()
	c.logger.Info("gateway connected", slog.String("gateway_url", c.cfg.GatewayURL))
	if err := c.serve(ws); err != nil {
		return true, err
	}
	return true, fmt.Errorf("gateway connection closed")
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) dial()
 * @Description //用新签发的 JWT 连接 gateway_url，不额外拼接 /ws
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: WebSocket 连接；拨号失败时返回 error
 */
func (c *Conn) dial() (*websocket.Conn, error) {
	token, err := jwt.Sign(c.cfg.GatewayKey, c.sessionID)
	if err != nil {
		return nil, err
	}
	endpoint, err := withToken(c.cfg.GatewayURL, token)
	if err != nil {
		return nil, err
	}

	dialer := websocket.Dialer{HandshakeTimeout: handshakeTimeout}
	conn, resp, err := dialer.DialContext(c.ctx, endpoint, nil)
	if resp != nil && resp.Body != nil {
		_ = resp.Body.Close()
	}
	if err != nil {
		return nil, fmt.Errorf("dial gateway: %w", err)
	}
	return conn, nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: withToken(gatewayURL, token string)
 * @Description //在已有网关地址上附加 token 查询参数
 * @Date :2026/10/23 10:39:00
 * @Param: gatewayURL 已含 /ws 的地址；token 连接 JWT
 * @return: 带 token 的连接地址；地址非法时返回 error
 */
func withToken(gatewayURL, token string) (string, error) {
	parsed, err := url.Parse(strings.TrimSpace(gatewayURL))
	if err != nil {
		return "", fmt.Errorf("parse gateway url: %w", err)
	}
	if parsed.Scheme != "ws" && parsed.Scheme != "wss" {
		return "", fmt.Errorf("gateway url scheme must be ws or wss")
	}
	if parsed.Host == "" {
		return "", fmt.Errorf("gateway url host is required")
	}
	query := parsed.Query()
	query.Set("token", token)
	parsed.RawQuery = query.Encode()
	return parsed.String(), nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) attach(ws *websocket.Conn)
 * @Description //把新套接字标记为当前可写连接
 * @Date :2026/10/23 10:39:00
 * @Param: ws 已拨通的连接
 * @return: 无
 */
func (c *Conn) attach(ws *websocket.Conn) {
	c.writeMu.Lock()
	c.ws = ws
	c.up.Store(true)
	c.writeMu.Unlock()
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) dropConn()
 * @Description //在写锁内关闭当前套接字，避免与写操作并发
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 无
 */
func (c *Conn) dropConn() {
	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	c.up.Store(false)
	if c.ws == nil {
		return
	}
	_ = c.ws.Close()
	c.ws = nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) serve(ws *websocket.Conn)
 * @Description //同时跑读循环和心跳，任一退出或连接被关闭就结束本轮
 * @Date :2026/10/23 10:39:00
 * @Param: ws 本轮连接
 * @return: 断线原因；主动关闭时为 context.Canceled
 */
func (c *Conn) serve(ws *websocket.Conn) error {
	loopCtx, cancel := context.WithCancel(c.ctx)
	defer cancel()

	errCh := make(chan error, 2)
	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		errCh <- c.readLoop(loopCtx, ws)
	}()
	go func() {
		defer wg.Done()
		errCh <- c.heartbeat(loopCtx, ws)
	}()

	var err error
	select {
	case err = <-errCh:
	case <-c.ctx.Done():
		err = c.ctx.Err()
	}
	cancel()
	c.closeSocket(ws)
	wg.Wait()
	return err
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) closeSocket(ws *websocket.Conn)
 * @Description //在写锁内关闭本轮套接字，避免和写帧并发
 * @Date :2026/10/23 10:39:00
 * @Param: ws 本轮连接
 * @return: 无
 */
func (c *Conn) closeSocket(ws *websocket.Conn) {
	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	if c.ws == ws {
		c.up.Store(false)
		c.ws = nil
	}
	_ = ws.Close()
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) readLoop(ctx context.Context, ws *websocket.Conn)
 * @Description //读取下行帧，解析 {to, from, data} 后交给回调
 * @Date :2026/10/23 10:39:00
 * @Param: ctx 本轮连接的取消上下文；ws 本轮连接
 * @return: 读失败或回调 panic 时返回 error，主动取消时返回 nil
 */
func (c *Conn) readLoop(ctx context.Context, ws *websocket.Conn) (err error) {
	defer func() {
		if rec := recover(); rec != nil {
			err = fmt.Errorf("read loop panic: %v", rec)
		}
	}()

	ws.SetReadLimit(maxFrameBytes)
	for {
		if ctx.Err() != nil {
			return nil
		}
		_, payload, readErr := ws.ReadMessage()
		if readErr != nil {
			if ctx.Err() != nil {
				return nil
			}
			return fmt.Errorf("read gateway frame: %w", readErr)
		}

		var frame model.WSMessage
		if unmarshalErr := json.Unmarshal(payload, &frame); unmarshalErr != nil {
			c.logger.Warn("unmarshal gateway frame failed", slog.Any("err", unmarshalErr))
			continue
		}
		if c.onFrame != nil {
			c.onFrame(payload, frame)
		}
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) heartbeat(ctx context.Context, ws *websocket.Conn)
 * @Description //每 30 秒向自己的 ws_session_id 发一帧，供网关保活
 * @Date :2026/10/23 10:39:00
 * @Param: ctx 本轮连接的取消上下文；ws 本轮连接
 * @return: 写失败时返回 error，主动取消时返回 nil
 */
func (c *Conn) heartbeat(ctx context.Context, ws *websocket.Conn) error {
	payload, err := json.Marshal(struct {
		To string `json:"to"`
	}{To: c.sessionID})
	if err != nil {
		return fmt.Errorf("marshal heartbeat: %w", err)
	}

	ticker := time.NewTicker(heartbeatInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			if writeErr := c.writeMessage(ws, payload); writeErr != nil {
				if ctx.Err() != nil {
					return nil
				}
				return writeErr
			}
		}
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Conn) writeMessage(ws *websocket.Conn, payload []byte)
 * @Description //在写锁内发送一条文本帧，避免 gorilla 并发写
 * @Date :2026/10/23 10:39:00
 * @Param: ws 期望写入的那一代连接；payload 文本帧
 * @return: 连接已换代时返回 ErrNotConnected，写失败时返回 error
 */
func (c *Conn) writeMessage(ws *websocket.Conn, payload []byte) error {
	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	if c.ws != ws || !c.up.Load() {
		return ErrNotConnected
	}
	if err := ws.SetWriteDeadline(time.Now().Add(writeWait)); err != nil {
		return fmt.Errorf("set write deadline: %w", err)
	}
	if err := ws.WriteMessage(websocket.TextMessage, payload); err != nil {
		c.up.Store(false)
		_ = ws.Close()
		return fmt.Errorf("write gateway frame: %w", err)
	}
	return nil
}
