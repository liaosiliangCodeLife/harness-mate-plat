/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //Hub 运行配置
 * @File: config.go
 * @Time: 2026/10/23 10:39:00
 * @All Rights Reserve By Brtc
 */

// Package config 从环境变量加载 Hub 运行配置。
package config

import (
	"os"
	"strings"
)

// Config 是 Hub 进程的全部运行参数，字段均来自环境变量。
type Config struct {
	// HTTPAddr 是 HTTP 监听地址，对应 HUB_HTTP_ADDR。
	HTTPAddr string
	// RedisURL 是 Redis 连接串，对应 REDIS_URL。
	RedisURL string
	// APIBaseURL 是 API 服务根地址，对应 API_BASE_URL。
	APIBaseURL string
	// InternalToken 是服务间令牌，对应 INTERNAL_TOKEN，可为空。
	InternalToken string
	// LogLevel 是日志级别，对应 LOG_LEVEL。
	LogLevel string
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: Load()
 * @Description //从环境变量加载 Hub 配置，缺省项使用默认值
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: *Config 配置对象；error 预留给非法配置，当前默认值下为 nil
 */
func Load() (*Config, error) {
	cfg := &Config{
		HTTPAddr:      getenv("HUB_HTTP_ADDR", ":8090"),
		RedisURL:      getenv("REDIS_URL", "redis://redis:6379/0"),
		APIBaseURL:    strings.TrimRight(getenv("API_BASE_URL", "http://api:5001"), "/"),
		InternalToken: strings.TrimSpace(os.Getenv("INTERNAL_TOKEN")),
		LogLevel:      getenv("LOG_LEVEL", "info"),
	}
	return cfg, nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: getenv(key, fallback string)
 * @Description //读取环境变量，空白时返回默认值
 * @Date :2026/10/23 10:39:00
 * @Param: key 环境变量名；fallback 变量为空时使用的默认值
 * @return: 去掉首尾空白后的配置值
 */
func getenv(key, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}
