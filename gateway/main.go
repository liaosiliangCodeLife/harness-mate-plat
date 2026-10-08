package main

import (
	"context"
	"errors"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"ws_gateway/config"
	jwtauth "ws_gateway/internal/jwt"
	gwlog "ws_gateway/internal/logging"
	redisstore "ws_gateway/internal/redis"
	"ws_gateway/internal/router"
	"ws_gateway/internal/ws"
)

// main 负责组装全部依赖并管理网关生命周期。
func main() {
	if err := run(); err != nil {
		logger := slog.New(slog.NewJSONHandler(os.Stderr, nil))
		logger.Error("ws gateway exited with error", slog.Any("err", err))
		os.Exit(1)
	}
}

func run() error {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg, err := config.Load()
	if err != nil {
		return err
	}

	logger, logCloser, err := gwlog.Setup(cfg.LogDir, cfg.LogLevel)
	if err != nil {
		return err
	}
	defer logCloser.Close()

	logger.Info(
		"ws gateway starting",
		slog.String("host", cfg.Host),
		slog.Int("port", cfg.Port),
		slog.String("instance", cfg.Instance),
		slog.String("log_dir", cfg.LogDir),
		slog.String("log_level", cfg.LogLevel),
	)

	redisClient, err := redisstore.NewClient(ctx, cfg.RedisURL, logger)
	if err != nil {
		return err
	}

	mapping := redisstore.NewMapping(redisClient, logger)
	pool := ws.NewSessionConnPool()
	msgRouter := router.New(pool, mapping, cfg.Instance, logger)
	verifier := jwtauth.NewVerifier(cfg.JWTSecret)

	server := ws.NewServer(
		cfg,
		logger,
		verifier,
		mapping,
		pool,
		msgRouter.RouteMessage,
	)

	subscriber := redisstore.NewSubscriber(redisClient, pool, logger)

	serverErrCh := make(chan error, 1)
	go func() {
		serverErrCh <- server.Start()
	}()

	pubsubErrCh := make(chan error, 1)
	go func() {
		pubsubErrCh <- subscriber.Subscribe(ctx)
	}()

	select {
	case <-ctx.Done():
		logger.Info("shutdown signal received")
	case err := <-serverErrCh:
		if err != nil {
			return err
		}
	case err := <-pubsubErrCh:
		if err != nil {
			return err
		}
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	var joined error

	if err := server.Shutdown(shutdownCtx); err != nil {
		joined = errors.Join(joined, err)
	}
	if err := pool.CloseAll(shutdownCtx); err != nil {
		joined = errors.Join(joined, err)
	}
	if err := redisClient.Close(); err != nil {
		joined = errors.Join(joined, err)
	}

	return joined
}
