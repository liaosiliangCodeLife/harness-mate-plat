package ws

import (
	"context"
	"log/slog"
	"net/http"

	"github.com/gorilla/websocket"
)

var websocketUpgrader = websocket.Upgrader{
	ReadBufferSize:  4096,
	WriteBufferSize: 4096,
	CheckOrigin: func(_ *http.Request) bool {
		return true
	},
}

func (s *WSServer) handleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := s.Upgrade(w, r)
	if err != nil {
		s.logger.Error("upgrade session failed", slog.Any("err", err))
	}
	if conn != nil {
		conn.Start()
	}
}

// Upgrade 完成 WebSocket 升级、JWT 验签、Redis 注册与连接池注册。
func (s *WSServer) Upgrade(w http.ResponseWriter, r *http.Request) (*SessionConn, error) {
	token := r.URL.Query().Get("token")
	claims, err := s.verifier.ParseSessionToken(token)
	if err != nil {
		http.Error(w, "invalid token", http.StatusUnauthorized)
		return nil, err
	}

	wsConn, err := websocketUpgrader.Upgrade(w, r, nil)
	if err != nil {
		return nil, err
	}

	sessionConn := NewSessionConn(
		claims.WSSessionID,
		wsConn,
		s.cfg.Instance,
		s.mapping,
		s.pool,
		s.logger.With(slog.String("ws_session_id", claims.WSSessionID)),
		s.messageHandler,
	)

	if err := s.mapping.SessionOnline(r.Context(), claims.WSSessionID, s.cfg.Instance); err != nil {
		_ = wsConn.Close()
		return nil, err
	}
	if err := s.pool.Add(sessionConn); err != nil {
		_ = sessionConn.Close(context.Background())
		return nil, err
	}

	s.logger.Info("session connected", slog.String("ws_session_id", claims.WSSessionID))
	return sessionConn, nil
}
