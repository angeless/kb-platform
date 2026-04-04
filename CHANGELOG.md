# 变更日志

所有重要变更都将被记录在此文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [0.49.4] — 2026-04-03

### 新增 (Added)
- 反思循环 v2 规则校验层：quality_check 新增 3 类检查——格式一致性（标题层级跳跃检测）、来源引用完整性（断言性语句无引用警告）、术语一致性（中英混用检测），每类可通过 pipeline config params 单独开关，9 个单元测试覆盖全部 AC（v0.49.4）

## [0.49.6] — 2026-04-03

### 新增 (Added)
- pgvector HNSW 索引：为 doc_embedding.embedding_vec 创建 HNSW 索引（m=16, ef_construction=64, CONCURRENTLY），从 JSONB embedding 列回填数据到 vector 列，语义搜索从 O(n) 降至 O(log n)，Alembic migration `v1w2x3y4z5a6`（v0.49.6）

## [0.49.3] — 2026-04-03

### 变更 (Changed)
- classify stage IR 适配：heading chunk 添加 [HEADING] 前缀提升分类权重，低置信度 chunk 标记 [LOW_QUALITY]，chunk 数据携带 structure_type/extraction_confidence/language 传给 orchestrator（v0.49.3）
- doc_generate stage IR 适配：fallback 模式按 structure_type 排序（heading 优先），heading 内容作为文档标题，低置信度 chunk 添加 OCR uncertainty 标注（v0.49.3）

## [0.49.2] — 2026-04-03

### 新增 (Added)
- 解析器 IR 字段填充：text_parser 设置 original_format/structure_type/extraction_confidence/language，asr_parser 设置 original_format/semantic_boundaries/language，URL import 设置 original_format/extraction_confidence/language，新增 ir_utils.py（语言检测 + 结构类型推断），tasks.py 映射 IR 字段到 AssetChunk（v0.49.2）

## [0.49.1] — 2026-04-03

### 新增 (Added)
- IR 中间表示字段：AssetChunk 新增 5 个 nullable 字段（original_format/structure_type/extraction_confidence/semantic_boundaries/language），向后兼容旧 chunk，Alembic migration `u0i1j2k3l4m5`（v0.49.1）

## [0.48.6] — 2026-04-03

### 新增 (Added)
- 前端资产列表视频增强：视频文件显示视频图标 + 时长标签（MM:SS 格式，从 Asset.tags.duration_s 读取），各类型资产显示对应图标（视频/音频/图片/PDF/其他），非视频文件不受影响（v0.48.6）

## [0.48.4] — 2026-04-03

### 新增 (Added)
- 视频帧提取 + OCR：扩展 video_parser 支持定时截取关键帧（默认每 30s），FFmpeg scene filter 去重，帧图片通过 ocr_parser 识别文字，有文字帧创建 AssetChunk（tags 含 source:video_frame + timestamp_s），适用于 PPT 录屏/白板场景，最大帧数限制 50（v0.48.4）

## [0.48.5] — 2026-04-03

### 新增 (Added)
- 文件恶意扫描：`malware_scanner.py` 通过 ClamAV daemon Unix socket 扫描上传文件，检测到恶意内容返回 400 拒绝上传，ClamAV 不可用时降级为允许上传并记录 WARNING，通过 `CLAMAV_ENABLED` 环境变量控制（默认关闭）（v0.48.5）
- 配置项：`clamav_enabled` (bool, default=False) + `clamav_socket` (str, default=/var/run/clamav/clamd.ctl)
- 单元测试 7 个用例覆盖全部 5 条验收标准

## [0.48.3] — 2026-04-03

### 新增 (Added)
- 视频解析器：`video_parser.py` 使用 FFmpeg 提取音轨交给 ASR 转文字、检测内嵌字幕创建独立 chunk、提取视频元数据（时长/分辨率/帧率），无 FFmpeg 时返回友好错误，临时文件完成后自动清理（v0.48.3）
- 解析器注册：`video` 类型映射到 video_parser，新增 `ffmpeg-python` 依赖
- 单元测试 10 个用例覆盖全部 6 条验收标准

## [0.48.2] — 2026-04-03

### 变更 (Changed)
- URL import 升级：`import_url()` 集成 readability 正文提取，AssetChunk 存储提取后纯文本（非原始 HTML），元数据（title/author/date）存入 chunk.tags，原始 HTML 仍保存在 MinIO 保留溯源，parse_status 设为 completed 跳过 worker 重处理（v0.48.2）

## [0.48.1] — 2026-04-03

### 新增 (Added)
- 网页正文提取模块：`readability.py` 使用 trafilatura 从 HTML 提取纯正文/标题/作者/日期，去除导航/广告/脚本噪音，提取失败时降级为简单 HTML 去标签（v0.48.1）
- 新增依赖：`trafilatura` 2.0.0 + `lxml_html_clean`
- 单元测试 8 个用例覆盖全部 5 条验收标准

## [0.47.8] — 2026-04-03

### 新增 (Added)
- 集成测试补全：3 个测试文件共 27 个用例，覆盖 ZIP 批量导入（端点结构/角色/文件上传/状态查询）、架构节点 CRUD（创建/更新/列表/角色控制/父子关系/租户隔离）、跨租户拒绝（依赖注入/服务层/路由层/模型层 kb_id 隔离验证）（v0.47.8）

## [0.47.7] — 2026-04-03

### 新增 (Added)
- 模型 API Key 轮换端点：`POST /v1/model-providers/{id}/rotate-key`（需 tenant_admin），使用 AES-256-GCM+PBKDF2 加密新 key，原子更新旧 key 立即失效，审计日志记录轮换事件（v0.47.7）
- 安全文档：`docs/security/model-key-encryption.md` 文档化加密方案（KDF2 格式、密钥管理、轮换流程）

## [0.47.6] — 2026-04-03

### 新增 (Added)
- Pipeline per-stage 执行日志表：新增 `pipeline_stage_log` 表（job_id FK、stage_name、status、started_at/finished_at、token_usage JSONB、error_message），Alembic 迁移 `t9h0i1j2k3l4`，pipeline worker 每个 stage 自动记录 running/completed/skipped/failed 状态，异常处理器同步记录失败日志（v0.47.6）

## [0.47.5] — 2026-04-03

### 新增 (Added)
- 审计日志保留策略：新增 `AUDIT_RETENTION_DAYS` 环境变量（默认90天），`cleanup_old_audit_logs()` 函数分批删除超期记录（每批1000行），`POST /v1/audit-logs/cleanup` 管理端点（需 tenant_admin 权限）手动触发清理（v0.47.5）

## [0.47.4] — 2026-04-03

### 新增 (Added)
- 数据库连接池显式配置：新增 `DB_POOL_SIZE`(默认10)、`DB_POOL_RECYCLE`(默认3600s)、`DB_MAX_OVERFLOW`(默认20) 环境变量，async/sync 引擎均使用统一配置，替换原硬编码值（v0.47.4）

## [0.47.3] — 2026-04-03

### 新增 (Added)
- Pipeline params JSON Schema 校验：PUT pipeline config 端点新增 `STAGE_PARAM_SCHEMAS` 验证，未知参数返回 422、类型不匹配返回 422、数值超范围返回 422，7 个 stage 全覆盖，GET 和 reset 不受影响（v0.47.3）

### 跳过 (Skipped)
- v0.47.2 suggest_tags entity_types：已在 v0.46.3 由 `_get_entity_types()` 实现，worker 端直接从 PipelineStageConfig 读取

## [0.47.1] — 2026-04-03

### 修复 (Fixed)
- 矛盾检测排除 draft 文档：`detect_contradictions` 查询从 `status.in_(["published", "draft"])` 修正为 `status != "draft"`，修复了双重 bug（`published` 不存在 + draft 不应参与），审计 C-3（v0.47.1）

## [未发布]

### 新增 (Added)
- 自动化开发工作流（dev-workflow-upgrade v1.3）
- PA Pass 统一认证接入：登录/注册/刷新代理到 Pass REST API，Pass JWT 为认证信任根，`GET /pass/me` 验证，首次登录自动创建 KB Tenant + User（v0.44.15）
- 前端图谱页矛盾/模式展示：图谱中矛盾边以红色粗虚线展示、"检测矛盾"按钮调用 AI 检测后自动刷新图谱、项目仪表盘新增"知识洞察"卡片展示矛盾统计 + 主题聚类 + 高频关联 + 知识缺口、"发现模式"按钮调用 AI 分析（v0.46.7）
- 前端 Pipeline 配置页：项目设置新增"知识提取配置" Tab，7 个 stage 卡片含启用/禁用开关，classify 支持置信度滑块 + 自定义实体类型标签输入，quality_check 支持最小内容长度 + 要求标题，conflict_detect 支持相似度阈值滑块，核心 stage 标注"核心"标签，支持重置为默认（v0.46.4）
- 跨文档模式发现：`POST /v1/projects/{id}/ai-discover-patterns`，LLM 分析项目文档的 summary/keywords 生成主题聚类、高频关联和知识缺口，结果 Redis 缓存 24h（v0.46.6）
- 跨文档矛盾检测：`POST /v1/projects/{id}/ai-detect-contradictions`，LLM 逐对比较文档事实一致性，检测到矛盾自动创建 contradicts 类型 CrossReference，severity 分三级，note 含证据（v0.46.5）
- 用户自定义实体类型支持：classify/doc_generate/suggest_tags prompt 动态注入 entity_types 指引，通过 pipeline config params 管理，未设置时行为不变（v0.46.3）
- Pipeline stage 运行时加载用户配置：run_pipeline 开头查询 PipelineStageConfig，disabled stage 跳过并发布 skipped 事件，config.params 传入各 stage 函数，quality_check 已参数化 min_content_length/require_title（v0.46.2）
- Pipeline stage 配置 DB 模型 + CRUD API：`pipeline_stage_config` 表（project_id + stage_name 联合唯一），GET 返回 7 stage 含默认值、PUT 更新单个 stage、POST reset 恢复默认，Alembic 迁移（v0.46.1）
- 前端文档列表虚拟滚动：@tanstack/react-virtual 虚拟化文档列表，pageSize 提升至 100，仅渲染可视区域行 + 10 行 overscan，快速滚动无白屏（v0.45.9）
- 摘要/标签置信度展示：ConfidenceBadge 组件（高/中/低三档颜色），低置信度时"重新生成"按钮高亮提示，旧数据无 confidence 时降级兼容（v0.45.14）
- 全局设置页重构：Tab 式布局（模型提供商 + 路由规则），路由规则支持 CRUD（添加/修改/删除），task_type 中文标签，tenant_admin 权限守卫（v0.45.12）
- 审计日志页面：`/admin/audit-logs` 路由（tenant_admin 可见），操作日志表格+操作类型/资源类型筛选器+分页，侧边栏增加权限感知导航入口（v0.45.11）
- 图谱页关系编辑：边展示中文关联类型标签、点击边弹出详情面板（来源/目标/类型）、editor+ 可删除关联、工具栏"添加关联"入口（v0.45.8）
- 文档详情页跨文档关联面板：CrossRefPanel 组件展示关联列表、editor+ 添加/删除关联（Modal 表单+文档搜索）、AI 建议关联一键确认（v0.45.7）
- AI 反思循环自检：generate_summary 和 suggest_tags 任务增加一轮 LLM 自我评审，置信度 < 0.7 自动使用修订版，summary_confidence 字段写入 DB 并通过 API 返回（v0.45.13）
- AI 摘要与标签推荐 API：`POST /v1/docs/{id}/ai-summarize` 和 `POST /v1/docs/{id}/ai-suggest-tags`，Celery 异步调用 LLM 生成摘要写入 summary 字段、推荐关键词写入 keywords 字段（v0.45.5）
- 文档导出支持 PDF/DOCX 格式：`GET /v1/docs/{id}/export?format=pdf|docx|markdown`，weasyprint PDF 渲染 + python-docx DOCX 生成，支持 CJK 字符（v0.45.2）
- 文档详情页导出下拉菜单：Markdown / PDF / DOCX 三格式选择，浏览器直接下载（v0.45.3）
- 审计日志写入集成：docs/projects/users 核心 CRUD 操作写入 audit_log 表（v0.45.10）
- 文档详情页摘要/标签区块：展示 AI 生成的摘要和关键词 chip，提供"生成摘要"和"推荐标签"按钮（v0.45.6）
- API 响应新增 summary/keywords/knowledge_type 字段到 KnowledgeDocOut 和 KnowledgeDocDetailOut（v0.45.6）
- knowledge_doc 表新增 summary 字段（Alembic 迁移 p5d6e7f8g9h0）（v0.45.4）
- 前端 RBAC 权限感知：usePermission hook + PermissionGuard 组件，按角色隐藏操作按钮（v0.44.1）
- 侧边栏精简：移除"用户管理"和"审计日志"入口，v1 单用户场景不需要（v0.44.2）
- 版本历史 API：GET /v1/docs/{id}/versions 列表 + POST rollback 回滚端点（v0.44.3）
- 前端版本历史 UI：历史版本抽屉面板 + 行级 diff 展示 + 回滚确认（v0.44.4）
- 批量导入后端：ZIP 上传解压 + 批次跟踪 + Celery 任务调度（v0.44.5）
- 前端批量导入 UI：BatchDropzone 拖拽上传 + BatchProgressList 轮询进度 + 资产页集成（v0.44.6）

### 修复 (Fixed)
- 全仓库 tenant_id → kb_id 重命名：7 表 Alembic migration + ORM + 36 router/service + JWT payload + 前端 store + 14 测试文件（v0.44.16）
- ForbiddenException 支持自定义 error_code 参数，修复封禁账号返回错误码不正确的问题（v0.44.15）
- 修复 3 处 `Depends(require_role())` 双层包装导致启动崩溃的 pre-existing bug（docs/graph/batch_import 路由）（v0.44.15）

### 变更 (Changed)
- 认证方式从本地 bcrypt + 自签 JWT 迁移到 PA Pass 代理模式（v0.44.15）
- 限流身份识别从 JWT 解码降级为 IP-based（KB 无法本地解码 Pass JWT）（v0.44.15）
- 注册流程：移除"团队名称"字段，新增可选"昵称"，注册后自动登录不再跳转登录页（v0.44.15）
- `/forgot-password` 和 `/reset-password` 端点标记为 410 Gone（密码管理移至 PA 平台）（v0.44.15）
- [P0] 首次体验修复：上传自动触发 ingest job、仪表板真实统计、资产列表运行流水线按钮、上传引导优化、OnboardingGuide 去 localStorage（v0.44.13）
- ASR 端到端打通：补齐 openai-whisper 依赖、修复 PARSEABLE_ASSET_TYPES 缺少 image/audio、延长 Celery 超时到 300s（v0.44.7）
- 图谱节点合并/拆分 API：POST merge + POST split 端点，事务安全，project_admin 权限（v0.44.8）
- 前端图谱编辑：分类管理面板 + NodeMergeModal + NodeSplitPanel，project_admin 专属（v0.44.9）
- API Key 限流：per-key Redis 固定窗口计数，rate_limit_per_minute 字段 + 429 响应（v0.44.10）
- API 用量统计：api_usage_log 表 + BackgroundTask 异步写入 + GET /v1/agent/usage 汇总查询（v0.44.11）
- Q&A 对话界面：SSE 流式问答页面 + 引用来源展示 + 项目首页问答入口 tile（v0.44.12）

## [0.43.5] - 2026-03-27

### 验收
- 全量回归通过：30 passed (ingestion) + 29 passed (frontend) + tsc 0 errors
- 新功能验收：Word 解析 / OCR-ASR 报错 / Agent API / 知识图谱 全部 PASS
- 验收报告：`docs/versions/v0.43-acceptance-report.md`

## [0.43.4] - 2026-03-27

### 新增
- 知识图谱 API：`GET /v1/projects/{id}/graph` 返回节点+边数据（T-43-04-B）
- 知识图谱前端：react-flow 交互图谱，节点按深度着色，点击跳转 Wiki（T-43-04-C/D/E）
- 项目详情页新增"图谱"入口卡片（T-43-04-F）
- GraphNode / GraphEdge / GraphResponse Pydantic schemas（T-43-04-A）

## [0.43.3] - 2026-03-27

### 新增
- Agent 输出接口：API Key 认证 + `/v1/agent/search` + `/v1/agent/ask`（T-43-03-E）
- API Key 管理：创建/列表/撤销端点 + 前端项目设置页 UI（T-43-03-C/F）
- `api_key` 数据库表 + Alembic 迁移（T-43-03-A）
- Agent API 接口文档 `docs/api/agent-api.md`（T-43-03-G）

## [0.43.2] - 2026-03-27

### 修复
- OCR 解析器：依赖缺失（Pillow/pytesseract/Tesseract）时抛出 RuntimeError 而非静默返回空（T-43-02-A）
- ASR 解析器：依赖缺失（whisper/ffmpeg）时抛出 RuntimeError 而非静默返回空（T-43-02-B）
- 修复图片/音频上传后"任务成功但知识库无内容"的 P0 bug

### 新增
- ingestion-worker Dockerfile 补全系统依赖：tesseract-ocr + tesseract-ocr-chi-sim + ffmpeg（T-43-02-C）

## [0.43.1] - 2026-03-27

### 修复
- Word 解析器：新增 word_parser.py，.docx 文件使用 python-docx 正确解析（T-43-01-A）
- 解析器路由修正：`docx` → word_parser，`doc` 旧格式标记为 unsupported（T-43-01-B）
- 修复 .docx 上传后数据丢失的 P0 bug（原因：.docx 被路由到 PDF 解析器）

### 新增
- Word 解析器支持 Heading 1/2/3 层级分组、超长文本自动拆分
- 8 个 word_parser 单元测试

## [0.42.10] - 2026-03-24

### 验收
- 上线清单 12.1-12.6 逐项验证通过（代码质量/安全/功能/基础设施/监控/运维）
- 修复：补回丢失的 Wiki 搜索页面

## [0.42.12] - 2026-03-24

### 安全修复
- 前端上传校验：文件类型白名单 + 大小限制 100MB (M-02/T-42-12-A)
- Alembic downgrade 数据保护：drop_table 改为 rename_table_backup (M-14/T-42-12-D)
- 邮箱唯一性改为租户隔离：UNIQUE(email, tenant_id) 替代全局 UNIQUE (M-15/T-42-12-E)

### 稳定性
- Celery 任务幂等性：重复投递已完成/失败的 job 自动跳过 (M-10/T-42-12-B)
- Dashboard 全局 ErrorBoundary：所有列表页组件内部报错显示友好提示 (M-12/T-42-12-C)

## [0.42.11] - 2026-03-24

### 安全修复
- WebSocket JWT 认证改用 httpOnly cookie，不再通过 URL query 传递 (H-03/T-42-11-A)
- Export 端点添加频率限制：10 次/分钟/用户 (M-07/T-42-11-D)

### 性能优化
- Embedding JSONB 回退搜索：消除 N+1 查询，批量获取文档；限制内存 500 条 (H-04/T-42-11-B)
- Settings 单例缓存：get_settings() 添加 @lru_cache (M-06/T-42-11-C)

## [0.42.9] - 2026-03-24

### 新增
- 邮件通知服务骨架：dev 模式写日志，production 模式 SMTP 发送 (T-42-09-A)
- 生产配置模板 .env.production.example (T-42-09-B)
- 健康检查增强：/readyz 增加 Alembic 版本检查 + 新增 /_version 端点 (T-42-09-C)
- 首次使用引导组件：新用户无项目时显示 4 步引导卡片 (T-42-09-D)
- 运维文档：部署指南 + 运维手册 + 升级指南 (T-42-09-E/F/G)

## [0.42.8] - 2026-03-24

### 新增
- Nginx 反向代理配置：HTTPS 终端、WebSocket 代理、静态资源缓存、安全头 (T-42-08-A)
- HTTPS 证书方案：自签脚本 + Let's Encrypt certbot 自动续签 (T-42-08-B)
- 生产 Docker Compose：资源限制、日志限制、restart policy、certbot 服务 (T-42-08-C)
- 备份脚本：PostgreSQL pg_dump + MinIO mirror + 恢复脚本 + crontab 模板 (T-42-08-D)
- 监控集成：Prometheus 采集 + Grafana 预置仪表盘（请求率/错误率/P95/连接数）(T-42-08-E)
- 一键部署脚本 deploy.sh：前置检查 + 构建 + 迁移 + 启动 + 健康检查 (T-42-08-F)

## [0.42.7] - 2026-03-24

### 新增
- 增量分类新增 RESTRUCTURE 类型：节点过载(>15篇)或跨域(>3节点)时触发结构变更建议 (T-42-07-A/B)
- 跨库索引系统：cross_reference 表 + Model + CRUD API (T-42-07-C/D/E/F)
  - `POST /v1/cross-refs` 创建引用
  - `GET /v1/cross-refs/doc/:id` 获取文档引用
  - `DELETE /v1/cross-refs/:id` 删除引用
  - `POST /v1/cross-refs/auto-suggest` 基于关键词自动建议引用
- 多库路由服务：`POST /v1/projects/route` 根据关键词返回 top-3 候选项目 (T-42-07-H/I)
- Project 模型新增 description 和 profile_keywords 字段 (T-42-07-G)
- Wiki 文档页展示跨库引用（同库链接 + 跨库标注项目名）(T-42-07-J)

### 变更
- 增量分类 prompt 增加 RESTRUCTURE 分类和 restructure_suggestion 输出字段

## [0.42.6] - 2026-03-23

### 新增
- 架构提议 MECE 原则：LLM 输出包含分类维度声明和覆盖度评分 (T-42-06-A)
- 架构质量门禁：深度限制 5 层、同级重名检测、叶子节点稀疏警告 (T-42-06-C)
- 文档生成元数据：每篇文档自动提取 keywords 和 knowledge_type (T-42-06-D/F)
- 审核页 MECE 信息卡：展示分类维度、覆盖度评分、未覆盖内容 (T-42-06-G)

### 变更
- 架构提议 prompt 增加 MECE 约束和分类维度选择指引 (T-42-06-A)
- Architecture.levels_json 扩展为包含 MECE 元数据的结构 (T-42-06-B)
- knowledge_doc 表新增 keywords (JSONB) 和 knowledge_type (VARCHAR) 列 (T-42-06-E)

## [0.42.5] - 2026-03-23

### 新增
- Wiki 知识浏览视图：三栏布局（架构树导航 + 文档正文 + 右侧 TOC）(T-42-05-A/B/D)
- Wiki 首页：架构概览卡片 + 最近更新文档列表 (T-42-05-K)
- 面包屑导航：显示文档在架构树中的路径 (T-42-05-C)
- 文内目录（TOC）：自动提取 h2/h3 标题，平滑滚动定位 (T-42-05-E)
- 来源追溯卡片：文档底部展示关联的原始素材 (T-42-05-F)
- 相关知识推荐：基于语义搜索显示 top-5 相关文档 (T-42-05-G)
- Wiki 内搜索：全文 + 语义混合搜索 (T-42-05-H)
- 项目详情页新增 Wiki 快捷入口 (T-42-05-J)

### 变更
- 项目详情页 Quick Stats 网格从 7 列扩展为 8 列

## [0.42.4] - 2026-03-22

### 新增
- 前端分页组件 `Pagination`（支持省略号、首尾页、禁用态）(T-42-04-A)
- 搜索结果分页：智能搜索和关键词搜索支持翻页导航 (T-42-04-B)
- QA 流式后端 SSE：`/v1/qa/ask` 支持 `stream=true` 参数，流式返回 LLM 响应 (T-42-04-C)
- QA 流式前端打字机效果：AI 回答逐字显示，带脉冲指示器 (T-42-04-D)
- QA 回答 Markdown 渲染：使用 `MarkdownView` 组件替代纯文本显示 (T-42-04-E)

### 变更
- QA 请求 schema 新增 `stream` 字段（默认 false，向后兼容）
- 搜索请求传递 `page`/`page_size` 参数给后端（后端已支持，此前前端未使用）

## [0.42.3] - 2026-03-22

### 安全修复
- Embedding upsert 原子化：delete+insert 改为 `INSERT ON CONFLICT DO UPDATE` (H-05/T-42-03)
- 账户登录锁定：连续 5 次失败锁定 15 分钟，Redis 计数器 (H-08/T-42-03)
- ZIP bomb 防护增强：目录深度限制 5 层，文件数上限 200 (M-04/T-42-03)
- Crypto salt 随机化：KDF2 格式使用 os.urandom(16) salt (M-05/T-42-03)
- Docker 端口收紧：PostgreSQL/Redis/MinIO-API 端口不再暴露到宿主机 (M-09/T-42-03)

### 新增
- test_login_lockout.py：登录锁定测试（6 个用例）
- test_crypto_salt.py：随机 salt + 三格式向后兼容测试（6 个用例）
- AUTH_ACCOUNT_LOCKED 错误码

## [0.42.2] - 2026-03-22

### 安全修复
- SSRF 防护增强：新增 DNS 解析检查，阻止 DNS rebinding 攻击 (H-01/T-42-02)
- CSRF 中间件：变更请求必须携带 X-Requested-With 头 (H-02/T-42-02)
- MinIO 凭证参数化：移除所有硬编码 minioadmin (H-07/T-42-02)
- Redis 密码保护：启用 requirepass + settings.py redis_password (H-09/T-42-02)

### 新增
- url_validator.py：独立 URL 验证器（含 DNS 解析 SSRF 检查）
- csrf.py：CSRF 中间件
- test_url_validator.py：SSRF 防护测试

## [0.42.1] - 2026-03-22

### 安全修复
- reset_token 仅在 development 环境返回，production 不再泄露明文 (C-04)
- QA decrypt 调用修复 (H-06)

### 修复
- forgot-password 页面语法错误 (C-01)
- 注册后跳转到 /login 并显示成功提示 (C-02)
- Dashboard 认证守卫竞态：添加 isCheckingAuth 状态 (C-03)

## [0.41.8] - 2026-03-22

### 安全修复
- docker-compose 移除所有硬编码默认密码，改为 `${VAR:?msg}` 强制注入 (T-41-08)

### 新增
- web.Dockerfile 前端生产构建容器（Node.js 20, 非 root 运行）(T-41-08)
- docker-compose 新增 web 前端服务定义
- .env.example 标注必填变量

## [0.41.7] - 2026-03-22

### 安全修复
- CORS allow_headers 从 `["*"]` 收紧为 `["Content-Type", "Authorization", "X-Request-ID"]` (T-41-07)

### 修改
- API 版本号从 VERSION 文件动态读取（不再硬编码）(T-41-07)

## [0.41.6] - 2026-03-22

### 新增
- 移动端汉堡菜单导航 mobile-nav.tsx (T-41-06)
- 状态徽章 aria-label 支持
- confirm-dialog aria 属性 (role=dialog, aria-modal)

### 修改
- dashboard layout 移动端响应式（侧边栏可折叠、主内容区全宽）
- 搜索页面移动端适配（按钮自适应）

## [0.41.5] - 2026-03-22

### 新增
- 全局 404 页面（中文友好提示 + 返回首页按钮）(T-41-05)
- 骨架屏加载组件 skeleton-card.tsx（替代"加载中..."纯文本）
- 错误恢复组件 error-retry.tsx（带重试按钮）
- 确认弹窗组件 confirm-dialog.tsx（退出登录等场景）
- 会话过期守卫 session-guard.tsx（过期后弹窗提示而非硬跳转）
- Toast 容器注入到 dashboard layout

### 修改
- dashboard layout 使用骨架屏替代纯文本加载
- api.ts 401 过期改为 dispatch session-expired 事件

## [0.41.4] - 2026-03-22

### 安全修复
- 搜索结果高亮改用安全 mark 解析器，消除 `dangerouslySetInnerHTML` XSS 风险 (T-41-04)

### 修改
- 新增 `label-maps.ts`：统一管理所有技术值→中文标签映射 (T-41-04)
- `status-badge.tsx` 改用 label-maps 映射（解析中→处理中，已解析→处理完成，失败→处理失败）
- 注册页面"组织名称"→"团队名称"
- 搜索结果"匹配字段"→"匹配位置"
- 新增 `highlight.ts`：安全 mark 标签解析器

## [0.41.3] - 2026-03-22

### 新增
- 混合搜索 API `POST /v1/search/hybrid`：关键词 + 语义双路检索，去重合并排序 (T-41-03)
- AI 问答 API `POST /v1/qa/ask`：RAG 模式（检索→LLM→答案+衍生问题）(T-41-03)
- 前端搜索页面三模式：智能搜索 / 关键词搜索 / AI 问答
- 搜索结果匹配类型标签（关键词/语义/双重匹配）
- 文档类型中文显示映射
- 衍生问题一键点击作为新搜索

## [0.41.2] - 2026-03-22

### 新增
- 前后端统一错误码系统：34 个错误码 + 中文消息映射 (T-41-02)
- 前端 `error-messages.ts` 错误码 → 中文消息映射表
- 前端 `error-toast.tsx` 通用错误 Toast 组件
- 后端 422 验证错误统一格式化处理

### 修改
- api.ts 错误拦截层改用 `getUserMessage()` 获取中文提示
- 网络断开时显示友好中文提示
- 500 错误统一显示"系统开了个小差，请稍后重试"

## [0.41.1] - 2026-03-22

### 安全修复
- WebSocket 租户隔离：连接前校验 project_id 归属，跨租户访问返回 4003 (T-41-01/S-01)
- Refresh Token 数据库记录：登录写入 hash、refresh 时校验 DB、logout 时吊销 (T-41-01/S-02)
- 修改密码时批量吊销所有 refresh token

### 新增
- `refresh_token` 数据库表（user_id, token_hash, expires_at, revoked）
- Alembic 迁移：`f5a6b7c8d9e0_add_refresh_token_table`

## [0.40.3] - 2026-03-22

### 修改
- 搜索结果高亮：后端使用 PostgreSQL ts_headline 生成带 mark 标记的摘要 (T-40-03)
- 前端搜索页面渲染高亮 snippet，匹配关键词黄色背景显示

## [0.40.2] - 2026-03-21

### 修改
- 文件上传组件：新增实时进度条显示（XHR `upload.onprogress`）(T-40-02)
- 支持取消上传（AbortController + xhr.abort）
- api.ts 新增 `uploadWithProgress()` 方法

## [0.40.1] - 2026-03-21

### 新增
- 忘记密码流程：`POST /v1/auth/forgot-password` + `POST /v1/auth/reset-password` (T-40-01)
- User 模型新增 `reset_token` 和 `reset_token_expires_at` 字段
- 前端忘记密码页面和重置密码页面
- 登录页面添加"忘记密码？"链接
- Alembic 迁移：`e4f5a6b7c8d9_add_password_reset_fields`
- 技术规范四件套（architecture.md, dev-governance.md, coding-standards.md, testing-strategy.md）
- UI 设计规范（交互式 HTML，12 个章节，双主题）
- CI 整合检查脚本 scripts/ci_verify.sh
- 冒烟测试 test_smoke.py
- VERSION 文件

### 修改 (Changed)
- CLAUDE.md 升级为双模式（产品模式 + 开发模式）
- 文档目录重组：PRD → docs/prd/，安全 → docs/security/，报告 → docs/reports/

## [0.39.6] - 2026-03-20

### 修改
- RateLimit 中间件：Redis 不可用时降级为本地内存固定窗口限流（50% 保守阈值）(T-39-06)
- 新增 OOM 防护（10K key 上限 + 60s 清理）和日志防风暴（60s 去重）

## [0.39.5] - 2026-03-20

### 新增
- 4 个服务的 requirements.lock 文件（精确锁定所有第三方依赖版本）(T-39-05)
- requirements.in 约束文件（记录依赖来源，支持 `uv pip compile` 重新生成）

### 修改
- 4 个 Dockerfile 改用 `--no-deps -r requirements.lock` 安装依赖，确保构建可重现 (T-39-05)

## [0.39.0] - 2026-03-20

### 新增
- .dockerignore 文件（减少构建上下文，保护敏感文件）(T-39-03)
- Celery 死信队列 DLQ 实现 (T-39-04)

### 修复
- build.yml Dockerfile 路径修复 (T-39-01)
- Docker 容器非 root 用户运行 (T-39-02)

## [0.35.1] - 2026-03-19

### 新增
- 完整的知识库管理后端 API（15 个路由模块）
- 文档生命周期管理（创建/编辑/审核/发布/版本管理）
- 架构树管理（fork/compare/rollback/节点分配）
- 全文搜索 + 语义搜索（tsvector + pgvector 双模式）
- Celery 异步任务系统（解析/流水线/AI 编排）
- JWT 认证 + RBAC 权限控制
- 多租户隔离
- MinIO 文件存储
- Prometheus 指标监控
- 前端 SPA（Next.js 15 + React 19）

---
