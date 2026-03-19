"use client";

import { useCallback, useState } from "react";
import { api, ApiClientError } from "@/lib/api";

interface FileUploadProps {
  projectId: string;
  onUploadComplete: () => void;
}

interface UploadItem {
  file: File;
  status: "pending" | "uploading" | "done" | "error";
  message?: string;
}

export function FileUpload({ projectId, onUploadComplete }: FileUploadProps) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const uploadFile = async (file: File, index: number) => {
    setItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, status: "uploading" } : item)),
    );

    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_id", projectId);
    formData.append("asset_type", guessType(file.name));

    try {
      await api.request("/v1/assets/upload", {
        method: "POST",
        body: formData,
      });
      setItems((prev) =>
        prev.map((item, i) => (i === index ? { ...item, status: "done" } : item)),
      );
    } catch (e) {
      const msg = e instanceof ApiClientError ? e.message : "上传失败";
      setItems((prev) =>
        prev.map((item, i) =>
          i === index ? { ...item, status: "error", message: msg } : item,
        ),
      );
    }
  };

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const newItems: UploadItem[] = Array.from(files).map((file) => ({
        file,
        status: "pending" as const,
      }));
      setItems((prev) => [...prev, ...newItems]);

      const startIndex = items.length;
      for (let i = 0; i < newItems.length; i++) {
        await uploadFile(newItems[i].file, startIndex + i);
      }
      onUploadComplete();
    },
    [items.length, projectId, onUploadComplete],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles],
  );

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${
          isDragOver
            ? "border-primary-400 bg-primary-50"
            : "border-gray-300 bg-gray-50 hover:border-gray-400"
        }`}
      >
        <p className="mb-2 text-sm text-gray-500">拖拽文件到此处，或</p>
        <label className="cursor-pointer rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
          选择文件
          <input
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files);
            }}
          />
        </label>
        <p className="mt-2 text-xs text-gray-400">
          支持 PDF、图片、音频、文本、Word、压缩包等格式
        </p>
      </div>

      {items.length > 0 && (
        <ul className="space-y-1">
          {items.map((item, i) => (
            <li key={i} className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm">
              <span className="truncate text-gray-700">{item.file.name}</span>
              <span
                className={
                  item.status === "done"
                    ? "text-green-600"
                    : item.status === "error"
                      ? "text-red-500"
                      : item.status === "uploading"
                        ? "text-primary-600"
                        : "text-gray-400"
                }
              >
                {item.status === "done"
                  ? "✓ 完成"
                  : item.status === "error"
                    ? item.message || "失败"
                    : item.status === "uploading"
                      ? "上传中..."
                      : "等待中"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function guessType(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    pdf: "pdf",
    png: "image", jpg: "image", jpeg: "image", gif: "image", webp: "image",
    mp3: "audio", wav: "audio", m4a: "audio", flac: "audio",
    mp4: "video", avi: "video", mov: "video",
    zip: "zip", rar: "zip", "7z": "zip", tar: "zip",
    doc: "doc", docx: "doc",
    txt: "text", md: "text", csv: "text",
  };
  return map[ext] || "document";
}
