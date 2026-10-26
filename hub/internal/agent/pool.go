/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //按 agent_id 管理上游 WebSocket 连接
 * @File: pool.go
 * @Time: 2026/10/23 10:39:00
 * @All Rights Reserve By Brtc
 */

// Package agent 维持 Hub 到网关的上游 WebSocket 连接。
package agent

import (
	"errors"
	"fmt"
	"log/slog"
	"sync"
)

// Pool 按 agent_id 保存上游连接。
type Pool struct {
	mu      sync.Mutex
	conns   map[string]*Conn
	logger  *slog.Logger
	onFrame FrameHandler
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: NewPool(logger *slog.Logger, onFrame FrameHandler)
 * @Description //创建一个空的上游连接池
 * @Date :2026/10/23 10:39:00
 * @Param: logger 日志；onFrame 收到下行帧时的回调
 * @return: *Pool
 */
func NewPool(logger *slog.Logger, onFrame FrameHandler) *Pool {
	return &Pool{
		conns:   make(map[string]*Conn),
		logger:  logger,
		onFrame: onFrame,
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (p *Pool) Get(cfg ConnConfig)
 * @Description //按 agent_id 取连接；没有则懒创建，网关配置变化则关掉旧连接重建
 * @Date :2026/10/23 10:39:00
 * @Param: cfg 本次发送携带的网关参数
 * @return: 对应 agent_id 的连接；新建连接尚未拨通
 */
func (p *Pool) Get(cfg ConnConfig) *Conn {
	p.mu.Lock()
	defer p.mu.Unlock()

	if existing, ok := p.conns[cfg.AgentID]; ok {
		if existing.sameGateway(cfg) {
			return existing
		}
		p.logger.Info(
			"gateway config changed, reconnecting",
			slog.String("agent_id", cfg.AgentID),
		)
		if err := existing.Close(); err != nil {
			p.logger.Warn(
				"close stale gateway connection failed",
				slog.String("agent_id", cfg.AgentID),
				slog.Any("err", err),
			)
		}
		delete(p.conns, cfg.AgentID)
	}

	conn := NewConn(cfg, p.logger, p.onFrame)
	conn.Start()
	p.conns[cfg.AgentID] = conn
	return conn
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (p *Pool) CloseAll()
 * @Description //关闭池中全部上游连接并等待它们退出
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 聚合后的关闭错误，全部成功时为 nil
 */
func (p *Pool) CloseAll() error {
	p.mu.Lock()
	conns := p.conns
	p.conns = make(map[string]*Conn)
	p.mu.Unlock()

	var joined error
	for agentID, conn := range conns {
		if err := conn.Close(); err != nil {
			joined = errors.Join(joined, fmt.Errorf("close agent %s: %w", agentID, err))
		}
	}
	return joined
}
