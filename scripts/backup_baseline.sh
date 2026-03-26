#!/bin/bash
# 基线备份脚本 - 2026-03-26
# 用于在重构前创建关键表的数据快照

set -e

BACKUP_DIR="data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/baseline_${TIMESTAMP}.sql"

echo "Creating baseline backup..."
echo "Backup file: ${BACKUP_FILE}"

# 从环境变量或配置文件读取数据库连接信息
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-fcli}"
DB_USER="${DB_USER:-fcli}"

# 导出关键表结构和数据
pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --table=dim_fund \
    --table=fact_fund_scale \
    --table=fact_gold_reserve \
    --table=watchlist_assets \
    --table=gold_supply_demand \
    --table=fact_gold_supply_demand \
    --table=dim_asset \
    --table=fact_quote \
    --table=dim_currency \
    --table=fact_fx_rate \
    --table=migrations \
    --no-owner \
    --no-acl \
    > "${BACKUP_FILE}"

echo "✓ Baseline backup created successfully"
echo "File size: $(du -h "${BACKUP_FILE}" | cut -f1)"

# 创建验证报告
echo ""
echo "=== Baseline Statistics ==="
echo "Backup timestamp: ${TIMESTAMP}"
echo "Tables backed up:"
echo "  - dim_fund"
echo "  - fact_fund_scale"
echo "  - fact_gold_reserve"
echo "  - watchlist_assets"
echo "  - gold_supply_demand"
echo "  - fact_gold_supply_demand"
echo "  - dim_asset"
echo "  - fact_quote"
echo "  - dim_currency"
echo "  - fact_fx_rate"
echo "  - migrations"
