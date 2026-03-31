"use client";

interface RollbackConfirmProps {
  version: number;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function RollbackConfirm({ version, onConfirm, onCancel, loading }: RollbackConfirmProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
        <h3 className="mb-2 text-lg font-semibold text-gray-900">确认回滚</h3>
        <p className="mb-4 text-sm text-gray-600">
          将文档内容回滚到版本 v{version}。此操作会创建一个新版本，原有版本不会被删除。
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? "回滚中..." : "确认回滚"}
          </button>
        </div>
      </div>
    </div>
  );
}
