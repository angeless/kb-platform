/**
 * Centralized label mapping: technical values → user-friendly Chinese labels.
 *
 * All frontend pages import from here. Backend still returns English enum values;
 * this file handles the display-layer translation.
 */

export const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  pending_review: "待审核",
  published: "已发布",
  rejected: "已驳回",
  pending: "等待中",
  parsing: "处理中",
  parsed: "处理完成",
  failed: "处理失败",
  unsupported: "暂不支持",
  active: "正常",
  disabled: "已禁用",
  completed: "已完成",
  running: "运行中",
  queued: "排队中",
};

export const DOC_TYPE_LABELS: Record<string, string> = {
  category: "分类",
  topic: "主题文档",
  document: "知识文档",
  glossary: "术语表",
  conflict: "待确认内容",
  index: "目录索引",
  concept: "概念",
  procedure: "流程",
  reference: "参考",
  tutorial: "教程",
  faq: "常见问题",
};

export const ASSET_TYPE_LABELS: Record<string, string> = {
  text: "文本文件",
  pdf: "PDF 文件",
  image: "图片文件",
  audio: "音频文件",
  video: "视频文件",
  archive: "压缩包",
  doc: "文档文件",
  zip: "压缩包",
};

export const ROLE_LABELS: Record<string, string> = {
  tenant_admin: "管理员",
  editor: "编辑",
  viewer: "查看者",
};

const LABEL_MAPS: Record<string, Record<string, string>> = {
  status: STATUS_LABELS,
  doc_type: DOC_TYPE_LABELS,
  asset_type: ASSET_TYPE_LABELS,
  role: ROLE_LABELS,
};

/**
 * Get a user-friendly label for a technical value.
 * Falls back to the original value if no mapping exists.
 */
export function getLabel(type: string, value: string): string {
  return LABEL_MAPS[type]?.[value] || value;
}
