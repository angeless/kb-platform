"use client";

interface SkeletonCardProps {
  rows?: number;
  hasTitle?: boolean;
}

export function SkeletonCard({ rows = 3, hasTitle = true }: SkeletonCardProps) {
  return (
    <div className="animate-pulse rounded-xl border border-gray-200 bg-white p-4">
      {hasTitle && <div className="mb-3 h-5 w-2/5 rounded bg-gray-200" />}
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="mb-2 h-3 rounded bg-gray-100"
          style={{ width: `${80 - i * 15}%` }}
        />
      ))}
    </div>
  );
}

export function SkeletonList({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
