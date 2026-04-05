import { cn } from "@/lib/utils";
import { STATUS_LABELS } from "@/lib/label-maps";

const statusStyles: Record<string, string> = {
  active: "bg-green-50 text-green-700",
  draft: "bg-gray-100 text-gray-600",
  reviewing: "bg-yellow-50 text-yellow-700",
  pending_review: "bg-yellow-50 text-yellow-700",
  published: "bg-blue-50 text-blue-700",
  archived: "bg-gray-100 text-gray-500",
  deleted: "bg-red-50 text-red-600",
  rejected: "bg-red-50 text-red-600",
  pending: "bg-orange-50 text-orange-600",
  parsing: "bg-indigo-50 text-indigo-600",
  parsed: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-600",
  running: "bg-indigo-50 text-indigo-600",
  queued: "bg-orange-50 text-orange-600",
  completed: "bg-green-50 text-green-700",
  unsupported: "bg-gray-100 text-gray-500",
  disabled: "bg-gray-100 text-gray-500",
  assigned: "bg-blue-50 text-blue-600",
  approved: "bg-green-50 text-green-700",
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const label = STATUS_LABELS[status] || status;
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
        statusStyles[status] || "bg-gray-100 text-gray-600",
        className,
      )}
      aria-label={`状态：${label}`}
    >
      {label}
    </span>
  );
}
