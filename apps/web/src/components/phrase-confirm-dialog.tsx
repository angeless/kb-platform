"use client";

import { useEffect, useState } from "react";

interface PhraseConfirmDialogProps {
  open: boolean;
  challenge: string;
  onConfirm: (phrase: string) => void;
  onCancel: () => void;
}

/**
 * Dialog for typed-phrase confirmation (428 CONFIRMATION_REQUIRED flow).
 * User must type the exact phrase shown in the challenge to proceed.
 */
export function PhraseConfirmDialog({
  open,
  challenge,
  onConfirm,
  onCancel,
}: PhraseConfirmDialogProps) {
  const [phrase, setPhrase] = useState("");

  useEffect(() => {
    if (open) setPhrase("");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="phrase-confirm-title"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="phrase-confirm-title" className="mb-2 text-lg font-semibold text-gray-900">
          操作确认
        </h3>
        <p className="mb-4 text-sm text-gray-500">{challenge}</p>
        <input
          type="text"
          value={phrase}
          onChange={(e) => setPhrase(e.target.value)}
          placeholder="请输入确认内容"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          autoFocus
          onKeyDown={(e) => {
            if (e.key === "Enter" && phrase.trim()) {
              onConfirm(phrase.trim());
            }
          }}
        />
        <div className="mt-4 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={() => phrase.trim() && onConfirm(phrase.trim())}
            disabled={!phrase.trim()}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
}
