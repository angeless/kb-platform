# KB Platform — 上线代办清单

> 版本：v0.42 → 生产上线
> 创建日期：2026-03-22
> 状态：进行中

---

## 使用方式

每完成一项，将 `[ ]` 改为 `[x]`。全部打勾后方可上线。

---

## 一、代码质量与安全（上线必须完成）

### 1.1 CRITICAL 问题修复

- [ ] C-01: forgot-password 页面语法错误已修复，页面可正常渲染
- [ ] C-02: 注册成功后跳转到 /login 并显示"注册成功"提示
- [ ] C-03: Dashboard 认证守卫移除 localStorage 检查，改为等待 checkAuth
- [ ] C-04: 生产环境 forgot-password API 不返回 reset_token
- [ ] H-06: QA 服务 decrypt 调用修复，AI 问答功能正常

### 1.2 安全加固

- [ ] SSRF 防护：import_url 拦截内网 IP 和 localhost
- [ ] CSRF 防护：变更请求需携带自定义头 `X-Requested-With`
- [ ] MinIO 凭证参数化：从 .env 读取，非默认值
- [ ] Redis 密码保护：配置 requirepass
- [ ] 账户锁定：连续 5 次登录失败锁定 15 分钟
- [ ] Embedding 原子 upsert：使用 ON CONFLICT
- [ ] ZIP bomb 防护：限制解压大小 / 文件数 / 目录深度
- [ ] Docker 端口收紧：DB/Redis/MinIO 不暴露到宿主机
- [ ] Crypto salt 随机化

### 1.3 代码审查

- [ ] 所有 v0.42 commit 已通过代码审查
- [ ] 无 TODO(SECURITY) 残留
- [ ] 无硬编码密码/密钥
- [ ] 无 `console.log` 泄露敏感数据
- [ ] 依赖无已知高危漏洞（`npm audit` + `pip audit`）

---

## 二、功能完整性（上线必须完成）

### 2.1 核心用户流程验证

- [ ] 注册 → 登录 → 创建项目 → 上传文件 → 查看解析结果
- [ ] 查看架构提议 → 审核架构 → 生成文档 → 浏览 Wiki
- [ ] 搜索（关键词 + 语义 + AI 问答）→ 查看结果 → 点击文档
- [ ] 编辑文档 → 保存 → 查看 diff
- [ ] 导出文档 → 下载 Markdown / ZIP
- [ ] 修改密码 → 登出 → 重新登录
- [ ] 忘记密码 → 重置密码（开发模式验证）
- [ ] 管理员邀请用户 → 新用户登录

### 2.2 新增功能验证

- [ ] Wiki 布局：左侧架构树导航正常
- [ ] Wiki 面包屑：路径正确
- [ ] Wiki TOC：自动生成文内目录
- [ ] 搜索分页：翻页正常
- [ ] QA 流式响应：逐字显示
- [ ] 跨库引用：创建/查看正常
- [ ] 多库路由：返回候选项目
- [ ] 新用户引导：首次登录展示

### 2.3 兼容性验证

- [ ] Chrome 最新版
- [ ] Firefox 最新版
- [ ] Safari 最新版
- [ ] iOS Safari（移动端）
- [ ] Android Chrome（移动端）

---

## 三、基础设施（上线必须完成）

### 3.1 生产环境配置

- [ ] `.env.production` 已创建（基于 `.env.production.example`）
- [ ] 所有必填项已填写（以下逐项确认）：

```
ENVIRONMENT=production                    # [ ] 已设置
POSTGRES_PASSWORD=<strong-random>         # [ ] 非默认值
JWT_SECRET=<64char-random>               # [ ] >=32字符随机串
ENCRYPTION_KEY=<32byte-key>              # [ ] >=32字符随机串
REDIS_PASSWORD=<strong-random>           # [ ] 已设置
MINIO_ROOT_USER=<custom>                 # [ ] 非 minioadmin
MINIO_ROOT_PASSWORD=<strong-random>      # [ ] 非 minioadmin
S3_ACCESS_KEY=<same-as-minio-user>       # [ ] 与 MinIO 一致
S3_SECRET_KEY=<same-as-minio-password>   # [ ] 与 MinIO 一致
CORS_ORIGINS=https://your-domain.com     # [ ] 仅允许生产域名
OPENAI_API_KEY=sk-xxx                    # [ ] 或 ANTHROPIC_API_KEY
```

### 3.2 数据库

- [ ] PostgreSQL 16 + pgvector 扩展已安装
- [ ] Alembic 迁移全部执行成功（`alembic upgrade head`）
- [ ] 数据库备份策略已配置（至少每日备份）
- [ ] 数据库连接池配置合理（建议 min=5, max=20）

### 3.3 文件存储

- [ ] MinIO / S3 bucket `kb-assets` 已创建
- [ ] 存储容量预估合理（建议初始 50GB）
- [ ] 备份策略已配置

### 3.4 Redis

- [ ] Redis 密码已配置
- [ ] 内存上限已设置（建议 512MB）
- [ ] 持久化已开启（RDB + AOF）

### 3.5 容器化

- [ ] `docker-compose.production.yml` 配置完成
- [ ] 所有容器使用非 root 用户
- [ ] 资源限制已配置（CPU/内存）
- [ ] 重启策略：`restart: unless-stopped`
- [ ] 日志配置：`logging.driver: json-file` + 大小限制

### 3.6 网络

- [ ] Nginx / Traefik 反向代理配置完成
- [ ] HTTPS 证书已配置（Let's Encrypt 或自签）
- [ ] HTTP → HTTPS 301 重定向
- [ ] WebSocket 代理配置（`/ws/` 路径）
- [ ] 静态资源 CDN 配置（可选）

---

## 四、监控与可观测性（上线必须完成）

### 4.1 健康检查

- [ ] `/healthz` 端点返回 200（含 DB/Redis/MinIO 检查）
- [ ] `/readyz` 端点返回 200（迁移完成）
- [ ] Docker healthcheck 配置正确
- [ ] 外部健康监控已接入（UptimeRobot / Pingdom / 自建）

### 4.2 日志

- [ ] 日志级别：生产环境 INFO
- [ ] 日志格式：JSON 结构化
- [ ] 日志收集：集中存储（ELK / Loki / 云服务）
- [ ] 敏感信息不记录（密码、token、API key）

### 4.3 指标（可选但强烈建议）

- [ ] Prometheus metrics 端点暴露
- [ ] Grafana dashboard 导入
- [ ] 关键告警规则：API 5xx > 10/min、Worker 失败 > 5/min、磁盘 > 85%

---

## 五、数据安全（上线必须完成）

### 5.1 备份

- [ ] 数据库：每日自动备份 + 至少保留 7 天
- [ ] MinIO 文件：定期快照 / 镜像
- [ ] 备份恢复测试：已验证至少一次完整恢复

### 5.2 密钥管理

- [ ] JWT_SECRET 为随机生成的 64+ 字符
- [ ] ENCRYPTION_KEY 为随机生成的 32 字节
- [ ] 所有 API Key 加密存储（AES-256-GCM）
- [ ] .env 文件不在版本控制中（.gitignore 确认）

### 5.3 访问控制

- [ ] 数据库端口不对外暴露
- [ ] Redis 端口不对外暴露
- [ ] MinIO 控制台端口不对外暴露（或有独立认证）
- [ ] 服务器 SSH 使用密钥认证（非密码）

---

## 六、运维准备（上线建议完成）

### 6.1 文档

- [ ] 部署文档：如何从零部署（`docs/operations/deploy-guide.md`）
- [ ] 运维手册：常见问题处理（`docs/operations/runbook.md`）
- [ ] API 文档：OpenAPI Swagger 可访问

### 6.2 回滚方案

- [ ] 回滚脚本准备（docker-compose down → 切换镜像版本 → up）
- [ ] 数据库回滚方案（Alembic downgrade 测试过，或使用备份恢复）
- [ ] 回滚演练至少执行一次

### 6.3 上线流程

- [ ] 上线时间窗口确定（建议工作日上午，避免周五）
- [ ] 上线操作人确定
- [ ] 回滚决策人确定
- [ ] 上线后 30 分钟巡检清单准备

---

## 七、上线后 30 分钟巡检清单

上线后立即执行：

- [ ] `/healthz` 返回 200
- [ ] 注册新账户成功
- [ ] 登录成功
- [ ] 创建项目成功
- [ ] 上传文件成功
- [ ] 搜索返回结果
- [ ] WebSocket 连接成功（任务状态推送）
- [ ] 日志无 ERROR / CRITICAL
- [ ] CPU / 内存正常（< 70%）
- [ ] Celery worker 活跃（`celery inspect ping`）

---

## 八、上线后 7 天跟踪

- [ ] 收集用户反馈
- [ ] 监控错误率趋势
- [ ] 监控 API 响应时间 P95
- [ ] 监控 Worker 任务成功率
- [ ] 评估是否需要 hotfix
- [ ] 规划 v0.43 迭代内容
