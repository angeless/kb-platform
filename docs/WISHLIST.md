# WISHLIST — 非 PRD 范围的改进建议

> 来源：2026-03-31 PRD vs 代码 Gap 分析
> 这些项目不在当前 PRD 范围内，但对生产就绪性和长期演进有价值。

---

## 基础设施 & 运维

### W-01 可观测性集成（Prometheus / OpenTelemetry）
- **现状**：仅 stdout 日志 + MetricsMiddleware（内存指标）
- **建议**：接入 Prometheus 指标导出 + OpenTelemetry 分布式追踪，覆盖 API → Celery → AI Orchestrator 全链路
- **价值**：生产环境故障定位从"猜"变为"看"

### W-02 数据库连接池优化
- **现状**：SQLAlchemy 使用默认连接池配置
- **建议**：显式配置 pool_size、pool_recycle、max_overflow，API（async）和 Pipeline Worker（sync）分别调优
- **价值**：防止高并发下连接耗尽

### W-03 水平扩展设计
- **现状**：Redis 单实例，MinIO 本地存储
- **建议**：Redis Sentinel/Cluster 支持；MinIO 分布式模式或迁移至 S3
- **价值**：支撑多实例部署

### W-04 Embedding 存储迁移（JSONB → pgvector）
- **现状**：DocEmbedding.embedding 用 JSONB 存储，pgvector 列存在但未迁移
- **建议**：完成 pgvector 原生列迁移，利用 IVFFlat/HNSW 索引加速语义搜索
- **价值**：语义搜索性能从 O(n) 降至 O(log n)

---

## 多租户 & 权限

### W-05 租户分级 / Feature Flags
- **现状**：Tenant 表仅 id、name、status 三个字段
- **建议**：增加 tier（free/pro/enterprise）、feature_flags（JSONB）、quota 限制
- **价值**：支持 SaaS 商业化和差异化功能

### W-06 用户组织层级
- **现状**：User 无 department/team 字段
- **建议**：增加组织层级支持，实现基于团队的权限分配
- **价值**：企业客户的组织架构映射

---

## 安全增强

### W-07 文件恶意扫描
- **现状**：上传文件仅检查格式和大小
- **建议**：集成 ClamAV 或类似引擎进行病毒扫描
- **价值**：防止恶意文件通过上传渠道进入系统

### W-08 审计日志保留策略
- **现状**：audit_log 表无清理机制，可能无限增长
- **建议**：增加 retention_days 配置，定期归档/清理旧日志
- **价值**：控制存储成本，满足合规要求

### W-09 模型 API Key 加密文档化 & 轮换
- **现状**：api_key_encrypted 字段存在但加密方式未文档化，无轮换机制
- **建议**：文档化加密方案（Fernet/AES），增加密钥轮换 API
- **价值**：安全审计合规

---

## Pipeline 增强

### W-10 Stage 重排序 / 条件执行
- **现状**：7 个 stage 顺序固定，仅支持 enable/disable
- **建议**：支持用户自定义 stage 执行顺序和条件（如：<100 篇文档时跳过 quality_check）
- **价值**：不同项目类型的灵活适配

### W-11 Per-Stage 幂等性保障
- **现状**：Asset 层有 file_hash 去重，但 sub-task 层无幂等性
- **建议**：每个 stage 记录 (doc_id, stage_name, input_hash) 防止重复处理
- **价值**：批量重跑安全性

### W-12 Pipeline 执行可观测性
- **现状**：Job 仅记录整体 status 和 error_message
- **建议**：增加 per-stage 执行日志表（stage_name, started_at, finished_at, token_usage, cost）
- **价值**：精细化成本追踪和性能分析

---

## Shiji-KB 借鉴方向（长期演进）

### W-13 多轮反思循环（Reflection Loop v2）
- **现状**：suggest_tags 有一次重试（confidence < 0.7）
- **建议**：实现规则校验层 + Agent 自我反思 + 人工抽检回馈的完整闭环
- **参考**：Shiji-KB 5 轮反思，准确率 90% → 99.1%

### W-14 SKILL 驱动 Pipeline
- **现状**：7 个硬编码 stage + params 配置
- **建议**：用户可上传/编辑自定义提取规则文档（SKILL 文件），stage 逻辑可热替换
- **参考**：Shiji-KB 54 个 SKILL 文档驱动处理

### W-15 知识本体建模 / 因果推理
- **现状**：实体+关键词（层1-2）+ 矛盾检测（层3雏形）+ 模式发现（层4雏形）
- **建议**：构建知识本体图（概念→关系→推理规则），实现跨文档逻辑链和因果推理
- **参考**：Shiji-KB 4 层语义模型

---

## 测试覆盖

### W-16 缺失的集成测试
- ZIP 导入端到端测试
- 术语表文档生成测试
- 架构节点 CRUD 完整测试
- 跨租户访问拒绝测试（虽然代码已安全，需要显式测试覆盖）

---

*最后更新：2026-03-31*
