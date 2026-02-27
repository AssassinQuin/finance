#!/bin/bash
# Docker 管理脚本

set -e

case "$1" in
    start)
        echo "启动所有服务..."
        docker-compose up -d
        ;;
    stop)
        echo "停止所有服务..."
        docker-compose down
        ;;
    restart)
        echo "重启所有服务..."
        docker-compose restart
        ;;
    status)
        echo "=== 服务状态 ==="
        docker-compose ps
        ;;
    logs)
        docker-compose logs -f ${2:-}
        ;;
    redis)
        echo "进入 Redis CLI..."
        docker exec -it fcli-redis redis-cli
        ;;
    mysql)
        echo "进入 MySQL..."
        docker exec -it fcli-mysql mysql -uroot -p123456zx fcli
        ;;
    backup)
        ./docker/backup-db.sh
        ;;
    restore)
        ./docker/restore-db.sh ${2:-}
        ;;
    clean)
        echo "清理未使用的资源..."
        docker system prune -f
        ;;
    *)
        echo "FCLI Docker 管理脚本"
        echo ""
        echo "用法: $0 {命令}"
        echo ""
        echo "命令:"
        echo "  start     启动所有服务"
        echo "  stop      停止所有服务"
        echo "  restart   重启所有服务"
        echo "  status    查看服务状态"
        echo "  logs      查看日志 (可指定服务名)"
        echo "  redis     进入 Redis CLI"
        echo "  mysql     进入 MySQL CLI"
        echo "  backup    备份数据库"
        echo "  restore   恢复数据库 (需指定文件)"
        echo "  clean     清理未使用的资源"
        ;;
esac
