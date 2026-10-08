package ws

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"

	"ws_gateway/config"
	jwtauth "ws_gateway/internal/jwt"
	redisstore "ws_gateway/internal/redis"
)

// WSServer 负责注册 HTTP 路由并承载 WebSocket 升级逻辑。
type WSServer struct {
	cfg            *config.Config
	logger         *slog.Logger
	verifier       *jwtauth.Verifier
	mapping        *redisstore.Mapping
	pool           *SessionConnPool
	messageHandler MessageHandler
	httpServer     *http.Server
}

// NewServer 创建一个绑定固定本地监听地址的 WS 服务。
func NewServer(
	cfg *config.Config,
	logger *slog.Logger,
	verifier *jwtauth.Verifier,
	mapping *redisstore.Mapping,
	pool *SessionConnPool,
	messageHandler MessageHandler,
) *WSServer {
	server := &WSServer{
		cfg:            cfg,
		logger:         logger,
		verifier:       verifier,
		mapping:        mapping,
		pool:           pool,
		messageHandler: messageHandler,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/ws", server.handleWS)
	mux.HandleFunc("/healthz", server.handleHealth)

	server.httpServer = &http.Server{
		Addr:    fmt.Sprintf("%s:%d", cfg.Host, cfg.Port),
		Handler: mux,
	}

	return server
}

// Start 启动本地 HTTP 服务并监听升级请求。
func (s *WSServer) Start() error {
	s.logger.Info("ws server listening", slog.String("addr", s.httpServer.Addr))
	err := s.httpServer.ListenAndServe()
	if err != nil && err != http.ErrServerClosed {
		return fmt.Errorf("listen and serve: %w", err)
	}
	return nil
}

// Shutdown 停止接受新连接，但不主动关闭已建立连接。
func (s *WSServer) Shutdown(ctx context.Context) error {
	return s.httpServer.Shutdown(ctx)
}

func (s *WSServer) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok"))
}
