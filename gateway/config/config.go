// Package config 负责从环境变量加载网关运行配置。
package config

import (
	"fmt"
	"strings"

	"github.com/spf13/viper"
)

// Config 描述 WS 网关运行所需的全部配置项。
type Config struct {
	// Host 是 HTTP 监听地址（127.0.0.1 仅本地，0.0.0.0 对外暴露）。
	Host string
	// Port 是本地 HTTP 监听端口。
	Port int
	// Instance 是当前网关实例标识，会写入 Redis 映射。
	Instance string
	// RedisURL 是 Redis 连接地址。
	RedisURL string
	// JWTSecret 是用于 HMAC JWT 验签的共享密钥。
	JWTSecret string
	// LogDir 是本地日志目录。
	LogDir string
	// LogLevel 是日志级别（debug/info/warn/error）。
	LogLevel string
}

// Load 从环境变量加载配置，并在缺少关键配置时返回错误。
func Load() (*Config, error) {
	v := viper.New()
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()

	v.SetDefault("ws_gateway.host", "127.0.0.1")
	v.SetDefault("ws_gateway.port", 8765)
	v.SetDefault("ws_gateway.instance", "gateway-001")
	v.SetDefault("redis.url", "redis://localhost:6379")
	v.SetDefault("ws_gateway.log_dir", "logs")
	v.SetDefault("ws_gateway.log_level", "debug")

	if err := v.BindEnv("ws_gateway.host", "WS_GATEWAY_HOST"); err != nil {
		return nil, fmt.Errorf("bind WS_GATEWAY_HOST: %w", err)
	}
	if err := v.BindEnv("ws_gateway.port", "WS_GATEWAY_PORT"); err != nil {
		return nil, fmt.Errorf("bind WS_GATEWAY_PORT: %w", err)
	}
	if err := v.BindEnv("ws_gateway.instance", "WS_GATEWAY_INSTANCE"); err != nil {
		return nil, fmt.Errorf("bind WS_GATEWAY_INSTANCE: %w", err)
	}
	if err := v.BindEnv("redis.url", "REDIS_URL"); err != nil {
		return nil, fmt.Errorf("bind REDIS_URL: %w", err)
	}
	if err := v.BindEnv("jwt.secret", "JWT_SECRET"); err != nil {
		return nil, fmt.Errorf("bind JWT_SECRET: %w", err)
	}
	if err := v.BindEnv("ws_gateway.log_dir", "WS_GATEWAY_LOG_DIR"); err != nil {
		return nil, fmt.Errorf("bind WS_GATEWAY_LOG_DIR: %w", err)
	}
	if err := v.BindEnv("ws_gateway.log_level", "WS_GATEWAY_LOG_LEVEL"); err != nil {
		return nil, fmt.Errorf("bind WS_GATEWAY_LOG_LEVEL: %w", err)
	}

	cfg := &Config{
		Host:      strings.TrimSpace(v.GetString("ws_gateway.host")),
		Port:      v.GetInt("ws_gateway.port"),
		Instance:  strings.TrimSpace(v.GetString("ws_gateway.instance")),
		RedisURL:  strings.TrimSpace(v.GetString("redis.url")),
		JWTSecret: strings.TrimSpace(v.GetString("jwt.secret")),
		LogDir:    strings.TrimSpace(v.GetString("ws_gateway.log_dir")),
		LogLevel:  strings.TrimSpace(v.GetString("ws_gateway.log_level")),
	}

	switch {
	case cfg.Port <= 0:
		return nil, fmt.Errorf("invalid WS_GATEWAY_PORT: %d", cfg.Port)
	case cfg.Instance == "":
		return nil, fmt.Errorf("WS_GATEWAY_INSTANCE is required")
	case cfg.RedisURL == "":
		return nil, fmt.Errorf("REDIS_URL is required")
	case cfg.JWTSecret == "":
		return nil, fmt.Errorf("JWT_SECRET is required")
	}

	return cfg, nil
}
