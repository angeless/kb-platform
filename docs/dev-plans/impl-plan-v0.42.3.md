# 实施计划 — v0.42.3 T-42-03 安全加固批次二

**创建时间**: 2026-03-22
**任务来源**: `docs/dev-plans/dev-plan-v0.42.md` → T-42-03
**基线版本**: v0.42.2 (commit 26989f9)

---

## §1 任务目标

修复 5 个安全问题：
- H-05: Embedding 删除-插入非原子操作 → 改为 upsert
- H-08: 无账户级登录锁定 → Redis 计数器 + 5 次锁定 15 分钟
- M-04: ZIP 上传无 archive bomb 检测增强 → 增加目录深度限制
- M-05: Crypto PBKDF2 使用确定性 salt → 随机 salt
- M-09: Docker 内部服务端口暴露到宿主机 → expose only

---

## §2 验收标准 Checklist

- [ ] 并发 embedding upsert 不产生重复记录
- [ ] 同一邮箱连续 5 次错误密码 → 423 "账户已临时锁定"
- [ ] 上传含 6 层嵌套目录的 ZIP → 400 错误
- [ ] 上传含 201 个文件的 ZIP → 400 错误
- [ ] 新加密数据使用随机 salt，旧数据仍可解密
- [ ] docker-compose 中 PostgreSQL/Redis 端口不暴露到宿主机

---

## §3 代码现状理解

| 文件 | 当前职责 | 相关发现 |
|------|---------|---------|
| `services/api/app/services/embedding_service.py` | embedding 生成与语义搜索 | L73-90: delete-then-insert 非原子 upsert |
| `packages/shared-models/shared_models/embedding.py` | DocEmbedding ORM 模型 | `doc_id` 已有 `unique=True` — 无需新增迁移 |
| `services/api/app/services/auth_service.py` | 认证：注册/登录/刷新/密码重置 | L70-100: login() 无失败计数 |
| `services/api/app/services/asset_service.py` | 文件上传和 ZIP 导入 | L176-280: import_archive 已有 max_files=100, 压缩比, 总大小检查。缺：目录深度、文件数应为200 |
| `services/api/app/utils/crypto.py` | AES-256-GCM 加解密 | L26-38: `_derive_key_pbkdf2` 使用 SHA-256(secret)[:16] 作为固定 salt |
| `docker-compose.yml` | 服务编排 | postgres(5432), redis(6379) 使用 `ports` 暴露到宿主机 |

---

## §4 实施步骤

### Step 1: T-42-03-A — Embedding 原子 upsert (H-05)

**跳过 T-42-03-A-migration** — `DocEmbedding.doc_id` 已有 `unique=True` 约束。

修改 `embedding_service.py` L73-90:
- 移除 `delete + add` 模式
- 改用 `sqlalchemy.dialects.postgresql.insert` + `on_conflict_do_update`
- 冲突键: `doc_id`
- 更新字段: `version`, `embedding`, `embedding_vec`, `model_name`, `dimensions`

### Step 2: T-42-03-B — 账户登录锁定 (H-08)

修改 `auth_service.py`:
- 在 `login()` 开头检查 Redis key `login:lockout:{email}`
- 若 key 存在 → raise 423 "账户已临时锁定，请 {剩余}分钟后重试"
- 密码验证失败 → 递增 Redis key `login:attempts:{email}` (TTL=15min)
- 达到 5 次 → 设置 `login:lockout:{email}` (TTL=15min)
- 密码验证成功 → 删除 attempts 和 lockout keys

依赖: `redis.asyncio` (已通过 settings.redis_password 可用)

### Step 3: T-42-03-C — ZIP bomb 防护增强 (M-04)

修改 `asset_service.py`:
- `max_files` 从 100 改为 200
- 新增 `MAX_ARCHIVE_DEPTH = 5`
- 在遍历条目时检查目录深度: `len(Path(entry).parts) > MAX_ARCHIVE_DEPTH`

### Step 4: T-42-03-D — Crypto salt 随机化 (M-05)

修改 `crypto.py`:
- 新增前缀 `_KDF2_PREFIX = b"KDF2"`
- 新增 `_derive_key_pbkdf2_random(secret, salt)` — 接受外部 salt
- `encrypt()` 使用随机 16 字节 salt: `KDF2(4B) + salt(16B) + nonce(12B) + ciphertext`
- `decrypt()` 支持三种格式: KDF2(新) → KDF1(旧) → legacy

### Step 5: T-42-03-E — Docker 端口收紧 (M-09)

修改 `docker-compose.yml`:
- postgres: `ports: ["5432:5432"]` → 删除 ports，添加 `expose: ["5432"]`
- redis: `ports: ["6379:6379"]` → 删除 ports，添加 `expose: ["6379"]`
- minio API 端口: `"9000:9000"` → 删除（仅内部通信），保留 `"9001:9001"` console 端口供开发调试

### Step 6: T-42-03-F — 测试 + 收尾

- 新增/更新测试文件
- VERSION → 0.42.3
- CHANGELOG 更新
- TODO_NEXT.md 更新

---

## §5 文件变更清单

| 文件路径 | 操作 | 变更内容 |
|---------|------|---------|
| `services/api/app/services/embedding_service.py` | 修改 | delete+add → pg upsert |
| `services/api/app/services/auth_service.py` | 修改 | 添加 Redis 登录锁定 |
| `services/api/app/services/asset_service.py` | 修改 | max_files=200, 目录深度检查 |
| `services/api/app/utils/crypto.py` | 修改 | 随机 salt + KDF2 格式 |
| `docker-compose.yml` | 修改 | postgres/redis ports → expose |
| `services/api/tests/test_login_lockout.py` | 新增 | 登录锁定测试 |
| `services/api/tests/test_crypto_salt.py` | 新增 | 随机 salt + 向后兼容测试 |

---

## §6 禁止文件核对

与 §1.7 Tier 1/2/3 禁止文件清单核对：无命中。所有修改文件均在任务定义范围内。

---

## §7 风险预判

| 风险 | 影响 | 缓解 |
|------|------|------|
| Crypto 格式变更导致旧数据无法解密 | 高 | decrypt() 保留三格式兼容链 |
| Redis 不可用导致登录全部失败 | 中 | lockout 检查异常时 fallback 放行（fail-open） |
| Docker 端口变更影响本地开发调试 | 低 | 仅影响直连 DB 的场景，服务内部通信不受影响 |

---

## §8 测试策略

- **单元测试**: crypto 新格式 + 向后兼容、embedding upsert 逻辑
- **API 测试**: 登录锁定 5 次 → 423、lockout 过期后可重新登录
- **集成测试**: ZIP 深度/文件数限制
- **手工验证**: docker-compose ports 变更、旧加密数据可解密
