#!/bin/bash
# Docker 容器信息脚本
# 生成时间: 2026-02-27

set -e

echo "=== FCLI Docker 容器信息 ==="
echo ""

# 检查容器状态
echo "1. 容器状态:"
docker ps --filter "name=fcli-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Redis 容器详情
echo "2. Redis 容器 (fcli-redis):"
echo "   - 镜像: redis:7-alpine"
echo "   - 端口: 6379"
echo "   - 数据卷: finance_redis_data:/data"
echo "   - 网络: finance_default"
echo "   - 命令: docker exec -it fcli-redis redis-cli"
echo ""

# MySQL 容器详情
echo "3. MySQL 容器 (fcli-mysql):"
echo "   - 镜像: mysql:9.6.0"
echo "   - 端口: 3306"
echo "   - 数据卷: finance_mysql_data:/var/lib/mysql"
echo "   - 网络: finance_default"
echo "   - 字符集: utf8mb4"
echo "   - 命令: docker exec -it fcli-mysql mysql -uroot -p"
echo ""

# 网络信息
echo "4. 网络信息:"
docker network inspect finance_default --format '{{.Name}}: {{.IPAM.Config}}'
echo ""

# 数据卷信息
echo "5. 数据卷:"
docker volume ls --filter "name=finance_"
echo ""

# 常用命令
echo "=== 常用命令 ==="
echo "启动所有服务:     docker-compose up -d"
echo "停止所有服务:     docker-compose down"
echo "查看日志:         docker-compose logs -f"
echo "重启服务:         docker-compose restart"
echo "进入 Redis:       docker exec -it fcli-redis redis-cli"
echo "进入 MySQL:       docker exec -it fcli-mysql mysql -uroot -p"
echo "备份数据库:       ./docker/backup-db.sh"
