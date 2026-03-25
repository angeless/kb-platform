# KB Platform — 运维手册

## 常见问题 SOP

### 1. 服务无响应

检查步骤：
1. docker compose ps 查看服务状态
2. docker compose logs --tail=50 <service> 查看日志
3. docker compose restart <service> 重启单个服务
4. 全部重启: down + up -d

### 2. 数据库连接耗尽

查看连接数: docker compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE datname='kb_platform';"
终止空闲: docker compose exec postgres psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='kb_platform' AND state='idle' AND state_change < now() - interval '10 minutes';"

### 3. 磁盘空间不足

1. df -h 检查磁盘
2. docker system prune -a --volumes 清理 Docker
3. find /opt/kb-platform/backups -mtime +3 -delete 清理旧备份

### 4. SSL 证书过期

1. openssl x509 -in infra/nginx/ssl/fullchain.pem -noout -dates 检查到期
2. docker compose exec certbot certbot renew --force-renewal 续签
3. docker compose exec nginx nginx -s reload 重载

### 5. Worker 任务积压

1. docker compose exec redis redis-cli LLEN celery 查看队列
2. docker compose logs --tail=100 pipeline-worker 查看日志
3. docker compose up -d --scale pipeline-worker=3 临时扩容

### 6. 数据库备份恢复

1. ls -lt backups/db/ 列出备份
2. bash infra/scripts/restore-db.sh <backup.sql.gz> 恢复
3. docker compose exec api alembic upgrade head 迁移

## 监控告警阈值

| 指标 | 阈值 | 处理 |
|------|------|------|
| API P95 延迟 | > 2s | 查慢查询/Worker积压 |
| API 错误率 | > 5% | 查 API 日志 |
| 磁盘使用率 | > 85% | 清理备份/Docker |
| DB 连接数 | > 80 | 查泄露/调连接池 |
| Redis 内存 | > 400MB | 查缓存/清理 |
