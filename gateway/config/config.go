// Package config 负责从环境变量加载网关运行配置。
package config

import (
	"fmt"
	"strings"
	"time"

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
	// JWTSecret 只在未配置平台地址时作为回退验签密钥。
	JWTSecret string
	// PlatformAPIBaseURL 是平台 API 根地址。为空时回退共享密钥验签。
	PlatformAPIBaseURL string
	// PlatformInternalToken 是调用平台内部接口的服务间令牌。
	PlatformInternalToken string
	// BotKeyCacheTTL 是 bot 验签密钥的本地缓存时间。
	BotKeyCacheTTL time.Duration
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
	v.SetDefault("platform.api_base_url", "")
	v.SetDefault("platform.internal_token", "")
	v.SetDefault("platform.bot_key_cache_ttl", "60s")
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
	if err := v.BindEnv("platform.api_base_url", "PLATFORM_API_BASE_URL"); err != nil {
		return nil, fmt.Errorf("bind PLATFORM_API_BASE_URL: %w", err)
	}
	if err := v.BindEnv("platform.internal_token", "PLATFORM_INTERNAL_TOKEN"); err != nil {
		return nil, fmt.Errorf("bind PLATFORM_INTERNAL_TOKEN: %w", err)
	}
	if err := v.BindEnv("platform.bot_key_cache_ttl", "PLATFORM_BOT_KEY_CACHE_TTL"); err != nil {
		return nil, fmt.Errorf("bind PLATFORM_BOT_KEY_CACHE_TTL: %w", err)
	}
	if err := v.BindEnv("ws_gateway.log_dir", "WS_GATEWAY_LOG_DIR"); err != nil {
		return nil, fmt.Errorf("bind WS_GATEWAY_LOG_DIR: %w", err)
	}
	if err := v.BindEnv("ws_gateway.log_level", "WS_GATEWAY_LOG_LEVEL"); err != nil {
		return nil, fmt.Errorf("bind WS_GATEWAY_LOG_LEVEL: %w", err)
	}

	ttlText := strings.TrimSpace(v.GetString("platform.bot_key_cache_ttl"))
	if ttlText == "" {
		ttlText = "60s"
	}
	cacheTTL, err := time.ParseDuration(ttlText)
	if err != nil || cacheTTL <= 0 {
		return nil, fmt.Errorf("invalid PLATFORM_BOT_KEY_CACHE_TTL: %s", ttlText)
	}

	cfg := &Config{
		Host:                  strings.TrimSpace(v.GetString("ws_gateway.host")),
		Port:                  v.GetInt("ws_gateway.port"),
		Instance:              strings.TrimSpace(v.GetString("ws_gateway.instance")),
		RedisURL:              strings.TrimSpace(v.GetString("redis.url")),
		JWTSecret:             strings.TrimSpace(v.GetString("jwt.secret")),
		PlatformAPIBaseURL:    strings.TrimSpace(v.GetString("platform.api_base_url")),
		PlatformInternalToken: strings.TrimSpace(v.GetString("platform.internal_token")),
		BotKeyCacheTTL:        cacheTTL,
		LogDir:                strings.TrimSpace(v.GetString("ws_gateway.log_dir")),
		LogLevel:              strings.TrimSpace(v.GetString("ws_gateway.log_level")),
	}

	switch {
	case cfg.Port <= 0:
		return nil, fmt.Errorf("invalid WS_GATEWAY_PORT: %d", cfg.Port)
	case cfg.Instance == "":
		return nil, fmt.Errorf("WS_GATEWAY_INSTANCE is required")
	case cfg.RedisURL == "":
		return nil, fmt.Errorf("REDIS_URL is required")
	case cfg.PlatformAPIBaseURL == "" && cfg.JWTSecret == "":
		return nil, fmt.Errorf("JWT_SECRET is required when PLATFORM_API_BASE_URL is empty")
	}

	return cfg, nil
}
