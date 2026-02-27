#!/bin/bash
# 数据库备份脚本
# 备份 MySQL 数据库结构

set -e

BACKUP_DIR="./docker/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/fcli_schema_${TIMESTAMP}.sql"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

echo "=== 开始备份数据库结构 ==="
echo "时间: $(date)"
echo ""

# 只备份结构（不含数据）
docker exec fcli-mysql mysqldump \
    -uroot -p123456zx \
    --no-data \
    --routines \
    --triggers \
    --events \
    --databases fcli \
    > ${BACKUP_FILE}

# 压缩备份文件
gzip ${BACKUP_FILE}

echo "备份完成: ${BACKUP_FILE}.gz"
echo ""

# 显示备份文件列表
echo "=== 备份文件列表 ==="
ls -lh ${BACKUP_DIR}/*.sql.gz 2>/dev/null || echo "暂无备份文件"
echo ""

# 清理超过30天的备份
echo "=== 清理旧备份 ==="
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +30 -delete
echo "完成"
