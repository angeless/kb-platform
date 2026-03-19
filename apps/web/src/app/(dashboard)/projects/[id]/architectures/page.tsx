"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface Architecture {
  id: string;
  name: string;
  version: string;
  status: string;
  created_at: string;
}

export default function ProjectArchitecturesPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [archs, setArchs] = useState<Architecture[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await api.get<Architecture[]>(
          `/v1/projects/${projectId}/architectures`,
        );
        setArchs(resp.data);
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
  }, [projectId]);

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">知识架构</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : archs.length === 0 ? (
        <div className="py-12 text-center text-gray-400">
          暂无架构。系统在解析资料后会自动生成架构草稿。
        </div>
      ) : (
        <div className="space-y-3">
          {archs.map((arch) => (
            <Link
              key={arch.id}
              href={`/architectures/${arch.id}`}
              className="block rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-900">{arch.name}</h3>
                    <StatusBadge status={arch.status} />
                  </div>
                  <p className="mt-1 text-sm text-gray-500">
                    版本 {arch.version} · 创建于{" "}
                    {new Date(arch.created_at).toLocaleDateString("zh-CN")}
                  </p>
                </div>
                <span className="text-gray-400">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
