// Package logging 负责初始化网关本地文件与控制台双输出日志。
package logging

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// multiHandler 将同一条日志写入多个 slog.Handler。
type multiHandler struct {
	handlers []slog.Handler
}

func (h *multiHandler) Enabled(ctx context.Context, level slog.Level) bool {
	for _, handler := range h.handlers {
		if handler.Enabled(ctx, level) {
			return true
		}
	}
	return false
}

func (h *multiHandler) Handle(ctx context.Context, record slog.Record) error {
	var joined error
	for _, handler := range h.handlers {
		if err := handler.Handle(ctx, record); err != nil {
			joined = fmt.Errorf("%w; %v", joined, err)
		}
	}
	return joined
}

func (h *multiHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	next := make([]slog.Handler, len(h.handlers))
	for i, handler := range h.handlers {
		next[i] = handler.WithAttrs(attrs)
	}
	return &multiHandler{handlers: next}
}

func (h *multiHandler) WithGroup(name string) slog.Handler {
	next := make([]slog.Handler, len(h.handlers))
	for i, handler := range h.handlers {
		next[i] = handler.WithGroup(name)
	}
	return &multiHandler{handlers: next}
}

// Setup 创建同时写入本地文件与控制台的 slog.Logger。
func Setup(logDir, levelName string) (*slog.Logger, io.Closer, error) {
	dir := strings.TrimSpace(logDir)
	if dir == "" {
		dir = "logs"
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, nil, fmt.Errorf("create log dir: %w", err)
	}

	logFile := filepath.Join(dir, fmt.Sprintf("ws_gateway-%s.log", time.Now().Format("2006-01-02")))
	file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return nil, nil, fmt.Errorf("open log file: %w", err)
	}

	level := ParseLevel(levelName)
	opts := &slog.HandlerOptions{
		Level:     level,
		AddSource: level <= slog.LevelDebug,
	}
	logger := slog.New(&multiHandler{
		handlers: []slog.Handler{
			slog.NewJSONHandler(file, opts),
			slog.NewJSONHandler(os.Stdout, opts),
		},
	})
	logger.Info(
		"logging initialized",
		slog.String("log_file", logFile),
		slog.String("level", level.String()),
	)
	return logger, file, nil
}

// ParseLevel 将字符串解析为 slog 日志级别，默认 debug。
func ParseLevel(levelName string) slog.Level {
	switch strings.ToLower(strings.TrimSpace(levelName)) {
	case "error":
		return slog.LevelError
	case "warn", "warning":
		return slog.LevelWarn
	case "info":
		return slog.LevelInfo
	default:
		return slog.LevelDebug
	}
}

// PayloadPreview 返回适合写入日志的消息体预览。
func PayloadPreview(payload []byte, max int) string {
	if max <= 0 {
		max = 512
	}
	text := strings.TrimSpace(string(payload))
	if text == "" {
		return ""
	}
	if len(text) <= max {
		return text
	}
	return text[:max] + "...(truncated)"
}
