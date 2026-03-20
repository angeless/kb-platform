# 开发起步 Checklist

## 1. 仓库初始化
- [ ] 创建 monorepo 根目录
- [ ] 建立 apps/services/packages/infra/openapi/examples 目录
- [ ] 写入 `manifest.json`
- [ ] 写入 `.env.example`
- [ ] 写入 `docker-compose.yml`

## 2. 基础设施
- [ ] 接入 PostgreSQL
- [ ] 接入 Redis
- [ ] 接入对象存储
- [ ] 接入消息队列或 Redis Stream
- [ ] 配置日志与审计链路

## 3. 核心最小闭环
- [ ] 上传材料
- [ ] 创建解析任务
- [ ] 生成统一中间格式
- [ ] 自动生成初版知识系统架构
- [ ] 人工审核架构
- [ ] 按架构生成知识文档草稿
- [ ] 审核并发布知识文档

## 4. 自检重点
- [ ] 任意产出都能追溯到来源
- [ ] 新材料能够判断新增/补充/修正/冲突
- [ ] 架构图修改后不会破坏已发布知识
- [ ] 模型 API Key 不落库明文
- [ ] 多租户数据不可串读
