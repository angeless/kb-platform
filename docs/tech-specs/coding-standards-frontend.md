# KB Platform 编码标准 — 前端规范

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**优先级**：条件必读（涉及前端时）

---

## 1. 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 15 | App Router 框架 |
| React | 19 | UI 库 |
| TypeScript | strict 模式 | 类型安全 |
| Tailwind CSS | 4 | 样式方案 |
| zustand | — | 全局状态管理 |
| vitest | — | 单元测试框架 |

---

## 2. 文件结构

```
apps/web/src/
├── app/                     # Next.js App Router 路由
│   ├── (auth)/              # 认证相关页面
│   ├── (dashboard)/         # 登录后页面
│   │   ├── knowledge-base/
│   │   │   ├── page.tsx     # 列表页
│   │   │   └── [id]/
│   │   │       └── page.tsx # 详情页
│   │   └── layout.tsx       # Dashboard 布局
│   ├── layout.tsx           # 根布局
│   └── error.tsx            # 全局错误页面
├── components/              # 可复用组件
│   ├── ui/                  # 基础 UI 组件（Button, Input, Modal...）
│   └── features/            # 业务组件
├── hooks/                   # 自定义 Hook
├── lib/                     # 工具库
│   ├── api.ts               # API 调用封装
│   └── utils.ts             # 通用工具函数
├── stores/                  # zustand store
└── types/                   # TypeScript 类型定义
```

---

## 3. 组件规范

### 3.1 基本规则

- 只使用函数式组件，禁止 class 组件
- 组件文件使用 PascalCase 命名（`KnowledgeUnitCard.tsx`）
- 每个组件文件导出一个主组件
- Props 使用 interface 定义，命名为 `{ComponentName}Props`

```tsx
interface KnowledgeUnitCardProps {
  unit: KnowledgeUnit;
  onSelect: (id: string) => void;
}

export function KnowledgeUnitCard({ unit, onSelect }: KnowledgeUnitCardProps) {
  return (
    <div className="rounded-lg border p-4" onClick={() => onSelect(unit.id)}>
      <h3 className="text-lg font-semibold">{unit.title}</h3>
    </div>
  );
}
```

### 3.2 状态管理

- 组件本地状态使用 `useState` / `useReducer`
- 跨组件全局状态使用 zustand（定义在 `stores/` 目录）
- 服务端数据通过 API 获取，不在 zustand 中缓存原始数据

### 3.3 API 调用

- 所有 API 调用通过 `lib/api.ts` 中的封装函数发起
- 每个 API 函数返回类型明确（不用 `any`）
- 请求和响应类型定义在 `types/` 目录

```tsx
// lib/api.ts
export async function getKnowledgeUnits(): Promise<KnowledgeUnit[]> {
  const response = await apiClient.get("/api/v1/knowledge-units");
  return response.data;
}
```

---

## 4. 样式规范

### 4.1 Tailwind CSS

- 使用 Tailwind 工具类编写样式
- 禁止使用内联 `style` 属性（除非动态计算值）
- 禁止使用 CSS Modules
- 复杂的重复样式组合使用 Tailwind `@apply` 或抽取为组件

### 4.2 响应式设计

- 移动优先：默认样式为移动端，使用 `md:` `lg:` 断点扩展
- 关键页面必须在 1024px 和 1440px 宽度下可用

---

## 5. TypeScript 规范

### 5.1 类型安全

- 启用 strict 模式（`tsconfig.json` 中 `strict: true`）
- 禁止使用 `any` 类型，除非绝对无法避免（必须注释说明原因）
- 使用 `unknown` 代替 `any` 进行类型收窄
- API 响应必须定义完整的类型

### 5.2 类型定义

- 共享类型定义在 `types/` 目录
- 组件 Props 类型在组件文件内定义
- 使用 `interface` 定义对象结构，`type` 用于联合类型和工具类型

---

## 6. 用户体验规范

### 6.1 加载状态

- 异步操作期间必须展示加载指示器（spinner、skeleton、progress bar）
- 禁止让用户面对空白页面等待

### 6.2 空状态

- 列表为空时展示有意义的提示信息和引导操作
- 禁止展示空白区域或仅显示空表格

### 6.3 错误状态

- 使用 `error-boundary.tsx` 包裹路由级组件
- API 错误展示用户友好的错误提示
- 提供重试操作（按钮或链接）

### 6.4 表单

- 使用受控组件管理表单状态
- 提交前进行客户端验证
- 提交过程中禁用提交按钮，防止重复提交
- 验证错误信息展示在对应字段旁

---

## 7. 可访问性

- 使用语义化 HTML 标签（`nav`、`main`、`section`、`article`）
- 交互元素必须有 `aria-label`（图标按钮、无文本链接）
- 表单字段必须关联 `label`
- 颜色不作为传达信息的唯一手段
- 支持键盘导航（Tab 顺序合理、Enter/Space 可触发操作）

---

## 8. 自定义 Hook

- 放在 `hooks/` 目录
- 文件名和函数名以 `use` 前缀开头
- 每个 Hook 职责单一
- 必须有 TypeScript 返回类型注解

```tsx
// hooks/useKnowledgeUnits.ts
export function useKnowledgeUnits(tenantId: string): {
  units: KnowledgeUnit[];
  isLoading: boolean;
  error: Error | null;
} {
  ...
}
```
