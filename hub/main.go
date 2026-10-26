/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //Hub 进程入口
 * @File: main.go
 * @Time: 2026/10/23 10:39:00
 * @All Rights Reserve By Brtc
 */

// Command hub 是纯转发进程：持有到网关的 WebSocket，把下行帧发布到 Redis 频道，并把 done 帧回写给 API。
package main

import (
	"context"
	"errors"
	"log/slog"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"hub/config"
	"hub/internal/agent"
	"hub/internal/backend"
	"hub/internal/model"
	"hub/internal/registry"
	"hub/internal/server"
)

/**
 * @Author liaosiliang1234@126.com
 * @Function: main()
 * @Description //执行 Hub 生命周期，失败时以非 0 退出
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 无
 */
func main() {
	if err := run(); err != nil {
		logger := slog.New(slog.NewJSONHandler(os.Stderr, nil))
		logger.Error("hub exited with error", slog.Any("err", err))
		os.Exit(1)
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: run()
 * @Description //加载配置、连接 Redis、启动 HTTP，并在信号到达后关闭全部上游连接
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 启动或关闭失败时返回 error
 */
func run() error {
	cfg, err := config.Load()
	if err != nil {
		return err
	}
	logger := newLogger(cfg.LogLevel)
	slog.SetDefault(logger)
	if cfg.InternalToken == "" {
		logger.Warn("INTERNAL_TOKEN is empty")
	}
	logger.Info(
		"hub starting",
		slog.String("http_addr", cfg.HTTPAddr),
		slog.String("api_base_url", cfg.APIBaseURL),
		slog.String("log_level", cfg.LogLevel),
	)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	store, err := registry.New(ctx, cfg.RedisURL, logger)
	if err != nil {
		return err
	}
	api := backend.New(cfg.APIBaseURL, cfg.InternalToken, logger)
	pool := agent.NewPool(logger, func(raw []byte, frame model.WSMessage) {
		dispatchFrame(logger, store, api, raw, frame)
	})
	httpServer := server.New(cfg, logger, pool)

	serverErrCh := make(chan error, 1)
	go func() {
		serverErrCh <- httpServer.Start()
	}()

	select {
	case <-ctx.Done():
		logger.Info("shutdown signal received")
	case err := <-serverErrCh:
		if err != nil {
			_ = pool.CloseAll()
			_ = store.Close()
			return err
		}
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	var joined error
	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		joined = errors.Join(joined, err)
	}
	if err := pool.CloseAll(); err != nil {
		joined = errors.Join(joined, err)
	}
	if err := store.Close(); err != nil {
		joined = errors.Join(joined, err)
	}
	return joined
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: newLogger(levelName string)
 * @Description //创建输出到标准输出的 JSON 日志
 * @Date :2026/10/23 10:39:00
 * @Param: levelName 日志级别名称
 * @return: *slog.Logger
 */
func newLogger(levelName string) *slog.Logger {
	level := parseLevel(levelName)
	return slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level:     level,
		AddSource: level <= slog.LevelDebug,
	}))
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: parseLevel(levelName string)
 * @Description //把日志级别字符串解析为 slog.Level，无法识别时使用 info
 * @Date :2026/10/23 10:39:00
 * @Param: levelName 配置中的级别名称
 * @return: slog.Level
 */
func parseLevel(levelName string) slog.Level {
	switch strings.ToLower(strings.TrimSpace(levelName)) {
	case "debug":
		return slog.LevelDebug
	case "warn", "warning":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: dispatchFrame(logger *slog.Logger, store *registry.Store, api *backend.Client, raw []byte, frame model.WSMessage)
 * @Description //把下行帧发布到账号 SSE 频道，并在 done 时异步回写 API
 * @Date :2026/10/24 17:50:49
 * @Param: logger 日志；store Redis；api 回写客户端；raw 原始帧；frame 已解析帧
 * @return: 无
 */
func dispatchFrame(logger *slog.Logger, store *registry.Store, api *backend.Client, raw []byte, frame model.WSMessage) {
	accountID, threadID, done := registry.RouteOf(frame)
	if accountID == "" || threadID == "" {
		logger.Warn(
			"skip redis publish, account_id or thread_id missing",
			slog.String("to", frame.To),
			slog.String("from", frame.From),
		)
	} else if err := store.Publish(accountID, raw); err != nil {
		logger.Error(
			"redis publish failed",
			slog.String("account_id", accountID),
			slog.String("thread_id", threadID),
			slog.Any("err", err),
		)
	}
	if done {
		api.DeliverAsync(raw)
	}
}
