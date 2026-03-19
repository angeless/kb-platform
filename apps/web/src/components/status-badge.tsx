import { cn } from "@/lib/utils";

const statusStyles: Record<string, string> = {
  active: "bg-green-50 text-green-700",
  draft: "bg-gray-100 text-gray-600",
  reviewing: "bg-yellow-50 text-yellow-700",
  published: "bg-blue-50 text-blue-700",
  archived: "bg-gray-100 text-gray-500",
  deleted: "bg-red-50 text-red-600",
  pending: "bg-orange-50 text-orange-600",
  parsing: "bg-indigo-50 text-indigo-600",
  parsed: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-600",
  running: "bg-indigo-50 text-indigo-600",
  completed: "bg-green-50 text-green-700",
  unsupported: "bg-gray-100 text-gray-500",
};

const statusLabels: Record<string, string> = {
  active: "活跃",
  draft: "草稿",
  reviewing: "审核中",
  published: "已发布",
  archived: "已归档",
  deleted: "已删除",
  pending: "待处理",
  parsing: "解析中",
  parsed: "已解析",
  failed: "失败",
  running: "运行中",
  completed: "已完成",
  unsupported: "暂不支持",
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
        statusStyles[status] || "bg-gray-100 text-gray-600",
        className,
      )}
    >
      {statusLabels[status] || status}
    </span>
  );
}
