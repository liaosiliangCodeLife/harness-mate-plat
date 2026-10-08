// Package ws 负责 WebSocket 连接升级、连接池管理、读写循环与心跳控制。
package ws

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/gorilla/websocket"

	redisstore "ws_gateway/internal/redis"
)

const (
	writeWait      = 10 * time.Second
	readTimeout    = 90 * time.Second
	sendBufferSize = 512
)

// MessageHandler 描述客户端消息进入路由层时的回调。
type MessageHandler func(conn *SessionConn, rawMsg []byte) error

// SessionConn 表示一个 ws_session_id 对应的 WebSocket 连接。
type SessionConn struct {
	// SessionID 是当前连接唯一标识（ws_session_id）。
	SessionID string
	// Conn 是底层 gorilla/websocket 连接对象。
	Conn *websocket.Conn
	// Send 是写循环唯一消费的发送队列。
	Send chan []byte
	// pongReq 是 readLoop 收到客户端 Ping 后交给 writeLoop 回复 Pong 的队列。
	pongReq chan string

	logger       *slog.Logger
	mapping      *redisstore.Mapping
	pool         *SessionConnPool
	instance     string
	routeMessage MessageHandler
	closed       chan struct{}
	closeOnce    sync.Once
	stateMu      sync.Mutex
	skipCleanup  bool
}

// SessionConnPool 管理所有本机在线会话连接。
type SessionConnPool struct {
	mu    sync.RWMutex
	conns map[string]*SessionConn
}

// NewSessionConnPool 创建一个会话连接池。
func NewSessionConnPool() *SessionConnPool {
	return &SessionConnPool{conns: make(map[string]*SessionConn)}
}

// Add 注册一个会话连接；若旧连接存在则会以替换模式关闭旧连接。
func (p *SessionConnPool) Add(conn *SessionConn) error {
	var previous *SessionConn

	p.mu.Lock()
	if existing, ok := p.conns[conn.SessionID]; ok {
		previous = existing
	}
	p.conns[conn.SessionID] = conn
	p.mu.Unlock()

	if previous != nil && previous != conn {
		_ = previous.Replace()
	}
	return nil
}

// Get 根据 ws_session_id 获取连接。
func (p *SessionConnPool) Get(sessionID string) (*SessionConn, bool) {
	p.mu.RLock()
	defer p.mu.RUnlock()
	conn, ok := p.conns[sessionID]
	return conn, ok
}

// Remove 删除会话连接映射，仅在映射仍指向同一连接时生效。
func (p *SessionConnPool) Remove(conn *SessionConn) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if existing, ok := p.conns[conn.SessionID]; ok && existing == conn {
		delete(p.conns, conn.SessionID)
	}
}

// CloseSession 关闭指定 ws_session_id 的本地连接。
func (p *SessionConnPool) CloseSession(ctx context.Context, sessionID string) error {
	conn, ok := p.Get(sessionID)
	if !ok {
		return nil
	}
	return conn.Close(ctx)
}

// CloseAll 关闭当前池中的全部连接。
func (p *SessionConnPool) CloseAll(ctx context.Context) error {
	p.mu.RLock()
	conns := make([]*SessionConn, 0, len(p.conns))
	for _, conn := range p.conns {
		conns = append(conns, conn)
	}
	p.mu.RUnlock()

	var joined error
	for _, conn := range conns {
		if err := conn.Close(ctx); err != nil {
			joined = errors.Join(joined, err)
		}
	}
	return joined
}

// NewSessionConn 创建一个新的会话连接对象。
func NewSessionConn(
	sessionID string,
	conn *websocket.Conn,
	instance string,
	mapping *redisstore.Mapping,
	pool *SessionConnPool,
	logger *slog.Logger,
	routeHandler MessageHandler,
) *SessionConn {
	return &SessionConn{
		SessionID:    sessionID,
		Conn:         conn,
		Send:         make(chan []byte, sendBufferSize),
		pongReq:      make(chan string, 1),
		logger:       logger,
		mapping:      mapping,
		pool:         pool,
		instance:     instance,
		routeMessage: routeHandler,
		closed:       make(chan struct{}),
	}
}

// Start 启动连接的读写循环。
func (c *SessionConn) Start() {
	go c.writeLoop()
	go c.readLoop()
}

// Enqueue 将消息送入写循环发送队列。
func (c *SessionConn) Enqueue(payload []byte) error {
	select {
	case <-c.closed:
		return fmt.Errorf("session connection already closed")
	default:
	}

	select {
	case c.Send <- payload:
		return nil
	default:
		return fmt.Errorf("session send queue is full")
	}
}

// Close 关闭连接，并清理连接池与 Redis 映射。
func (c *SessionConn) Close(ctx context.Context) error {
	var result error

	c.closeOnce.Do(func() {
		close(c.closed)
		c.pool.Remove(c)
		c.stateMu.Lock()
		skipCleanup := c.skipCleanup
		c.stateMu.Unlock()

		if err := c.Conn.Close(); err != nil && !websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
			result = errors.Join(result, fmt.Errorf("close session websocket: %w", err))
		}
		if !skipCleanup {
			if err := c.mapping.SessionOffline(ctx, c.SessionID); err != nil {
				result = errors.Join(result, err)
			}
		}
		c.logger.Info("session connection closed", slog.String("ws_session_id", c.SessionID))
	})

	return result
}

// Replace 将当前连接标记为被新连接替换，并触发底层连接关闭。
func (c *SessionConn) Replace() error {
	c.stateMu.Lock()
	c.skipCleanup = true
	c.stateMu.Unlock()
	return c.Conn.Close()
}

func (c *SessionConn) readLoop() {
	defer func() {
		if err := c.Close(context.Background()); err != nil {
			c.logger.Error("close session connection from read loop failed", slog.Any("err", err))
		}
	}()

	c.Conn.SetReadLimit(1024 * 1024)
	if err := c.Conn.SetReadDeadline(time.Now().Add(readTimeout)); err != nil {
		c.logger.Error("set session read deadline failed", slog.Any("err", err))
		return
	}
	c.Conn.SetPingHandler(func(appData string) error {
		if err := c.Conn.SetReadDeadline(time.Now().Add(readTimeout)); err != nil {
			return err
		}
		select {
		case c.pongReq <- appData:
		default:
		}
		return nil
	})

	for {
		_, payload, err := c.Conn.ReadMessage()
		if err != nil {
			if !websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
				c.logger.Warn(
					"read session message failed",
					slog.String("ws_session_id", c.SessionID),
					slog.Any("err", err),
				)
			}
			return
		}
		if c.routeMessage == nil {
			c.logger.Warn("session route handler is nil", slog.String("ws_session_id", c.SessionID))
			continue
		}
		if err := c.routeMessage(c, payload); err != nil {
			c.logger.Error(
				"route session message failed",
				slog.String("ws_session_id", c.SessionID),
				slog.Any("err", err),
			)
		}
		if err := c.Conn.SetReadDeadline(time.Now().Add(readTimeout)); err != nil {
			c.logger.Error("refresh session read deadline failed", slog.Any("err", err))
			return
		}
	}
}

func (c *SessionConn) writeLoop() {
	defer func() {
		if err := c.Close(context.Background()); err != nil {
			c.logger.Error("close session connection from write loop failed", slog.Any("err", err))
		}
	}()

	for {
		select {
		case <-c.closed:
			return
		case payload := <-c.Send:
			if err := c.Conn.SetWriteDeadline(time.Now().Add(writeWait)); err != nil {
				c.logger.Error("set session write deadline failed", slog.Any("err", err))
				return
			}
			if err := c.Conn.WriteMessage(websocket.TextMessage, payload); err != nil {
				c.logger.Warn(
					"write session message failed",
					slog.String("ws_session_id", c.SessionID),
					slog.Any("err", err),
				)
				return
			}
		case appData := <-c.pongReq:
			if err := c.Conn.SetWriteDeadline(time.Now().Add(writeWait)); err != nil {
				c.logger.Error("set session pong deadline failed", slog.Any("err", err))
				return
			}
			if err := c.Conn.WriteMessage(websocket.PongMessage, []byte(appData)); err != nil {
				c.logger.Warn(
					"pong session connection failed",
					slog.String("ws_session_id", c.SessionID),
					slog.Any("err", err),
				)
				return
			}
		}
	}
}
