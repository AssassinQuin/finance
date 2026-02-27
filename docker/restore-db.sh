#!/bin/bash
# 数据库恢复脚本

set -e

if [ -z "$1" ]; then
    echo "用法: $0 <备份文件.sql.gz>"
    echo ""
    echo "可用备份文件:"
    ls -lh ./docker/backups/*.sql.gz 2>/dev/null || echo "暂无备份文件"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "=== 开始恢复数据库 ==="
echo "备份文件: $BACKUP_FILE"
echo "时间: $(date)"
echo ""

# 解压并恢复
gunzip -c ${BACKUP_FILE} | docker exec -i fcli-mysql mysql -uroot -p123456zx

echo ""
echo "恢复完成!"
