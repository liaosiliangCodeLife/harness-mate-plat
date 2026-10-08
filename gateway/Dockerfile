# syntax=docker/dockerfile:1

FROM golang:1.25-alpine AS builder

WORKDIR /src

RUN apk add --no-cache ca-certificates git

COPY go.mod go.sum ./
RUN go mod download

COPY . .

ARG VERSION=v0.0.3

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags "-s -w" \
    -o /out/ws_gateway \
    .

FROM alpine:3.21

ARG VERSION=v0.0.3
LABEL org.opencontainers.image.version="${VERSION}"

RUN apk add --no-cache ca-certificates wget \
    && adduser -D -g '' appuser

WORKDIR /app

COPY --from=builder /out/ws_gateway /app/ws_gateway

RUN mkdir -p /app/logs \
    && chown -R appuser:appuser /app

ENV WS_GATEWAY_HOST=0.0.0.0 \
    WS_GATEWAY_PORT=8765 \
    WS_GATEWAY_INSTANCE=gateway-001 \
    WS_GATEWAY_LOG_DIR=logs \
    WS_GATEWAY_LOG_LEVEL=info

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- "http://127.0.0.1:${WS_GATEWAY_PORT}/healthz" || exit 1

USER appuser

ENTRYPOINT ["/app/ws_gateway"]
