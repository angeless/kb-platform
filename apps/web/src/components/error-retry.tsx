"use client";

interface ErrorRetryProps {
  message: string;
  onRetry: () => void;
}

export function ErrorRetry({ message, onRetry }: ErrorRetryProps) {
  return (
    <div className="rounded-lg bg-red-50 p-4">
      <p className="mb-3 text-sm text-red-600">{message}</p>
      <button
        onClick={onRetry}
        className="rounded-lg bg-red-100 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-200"
      >
        重试
      </button>
    </div>
  );
}
