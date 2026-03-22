/**
 * Error code → user-friendly Chinese message mapping.
 *
 * Frontend displays these messages instead of raw error codes or HTTP statuses.
 * The backend message field takes priority; this map is the fallback.
 */

export const ERROR_MESSAGES: Record<string, string> = {
  // Auth
  AUTH_INVALID_CREDENTIALS: "邮箱或密码不正确",
  AUTH_TOKEN_EXPIRED: "登录已过期，请重新登录",
  AUTH_TOKEN_INVALID: "身份验证失败，请重新登录",
  AUTH_INSUFFICIENT_ROLE: "您没有权限执行此操作",
  AUTH_EMAIL_ALREADY_EXISTS: "该邮箱已被注册",
  AUTH_REFRESH_TOKEN_INVALID: "登录已失效，请重新登录",
  AUTH_RESET_TOKEN_INVALID: "重置链接已失效，请重新申请",

  // Project
  PROJECT_NOT_FOUND: "项目不存在或已被删除",
  PROJECT_NAME_DUPLICATE: "项目名称已存在，请换一个",

  // Asset
  ASSET_NOT_FOUND: "文件不存在或已被删除",
  ASSET_DUPLICATE_HASH: "该文件已上传过，无需重复上传",
  ASSET_TYPE_NOT_ALLOWED: "不支持该文件格式",
  ASSET_TOO_LARGE: "文件大小超出限制",

  // Architecture
  ARCH_NOT_FOUND: "知识架构不存在",
  ARCH_NODE_NOT_FOUND: "分类节点不存在",
  ARCH_ALREADY_PUBLISHED: "该架构已发布，无法再次发布",
  ARCH_CYCLE_DETECTED: "检测到循环引用，请调整节点关系",

  // Knowledge Doc
  DOC_NOT_FOUND: "文档不存在或已被删除",
  DOC_ALREADY_PUBLISHED: "该文档已发布",
  DOC_STATUS_INVALID: "文档当前状态不允许此操作",

  // Job
  JOB_NOT_FOUND: "任务不存在",
  JOB_ALREADY_RUNNING: "该任务正在运行中，请等待完成",

  // Conflict
  CONFLICT_NOT_FOUND: "冲突记录不存在",
  CONFLICT_ALREADY_RESOLVED: "该冲突已解决",

  // Model
  MODEL_PROVIDER_NOT_FOUND: "模型服务未配置",
  MODEL_ROUTE_NOT_FOUND: "未找到匹配的模型路由",
  MODEL_PROVIDER_UNREACHABLE: "AI 服务暂时不可用，请稍后重试",

  // User
  USER_NOT_FOUND: "用户不存在",

  // Search
  SEARCH_QUERY_TOO_SHORT: "请输入至少 2 个字的搜索内容",
  QA_MODEL_NOT_CONFIGURED: "AI 问答功能需要先配置模型服务",

  // Validation
  VALIDATION_ERROR: "提交的信息有误，请检查后重试",

  // System
  SYSTEM_INTERNAL_ERROR: "系统开了个小差，请稍后重试",
  SYSTEM_RATE_LIMITED: "操作太频繁，请稍后再试",
  SYSTEM_SSRF_BLOCKED: "该地址不允许访问",

  // Upload (frontend-only)
  UPLOAD_CANCELLED: "上传已取消",
  NETWORK_ERROR: "网络连接失败，请检查网络后重试",
  PARSE_ERROR: "数据解析失败，请稍后重试",
};

/**
 * Get user-friendly message for an error code.
 * Prefers backend message if available, falls back to local mapping.
 */
export function getUserMessage(errorCode: string, backendMessage?: string): string {
  // Backend message takes priority (it's already in Chinese)
  if (backendMessage && backendMessage !== errorCode) {
    return backendMessage;
  }
  return ERROR_MESSAGES[errorCode] || "操作失败，请稍后重试";
}
