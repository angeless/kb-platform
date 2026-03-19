"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { useJobs, useRetryJob } from "@/hooks/useJobs";

const jobTypeLabels: Record<string, string> = {
  ingest: "资料解析",
  classify: "内容分类",
  architecture_draft: "架构生成",
  kb_generate: "文档生成",
  review_publish: "审核发布",
};

export default function ProjectJobsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useJobs(projectId, page);
  const retryJob = useRetryJob();

  const jobs = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  const handleRetry = async (jobId: string) => {
    try {
      await retryJob.mutateAsync(jobId);
    } catch {
      // error available via retryJob.error
    }
  };

  const formatDuration = (start: string | null, end: string | null) => {
    if (!start) return "—";
    const s = new Date(start).getTime();
    const e = end ? new Date(end).getTime() : Date.now();
    const seconds = Math.round((e - s) / 1000);
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  };

  const errorMessage =
    error instanceof ApiClientError ? error.message :
    retryJob.error instanceof ApiClientError ? retryJob.error.message :
    error ? "加载失败" :
    retryJob.error ? "重试失败" : "";

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">任务监控</h1>
          <p className="mt-1 text-sm text-gray-500">共 {total} 个任务 · 每 10 秒自动刷新</p>
        </div>
        <button
          onClick={() => refetch()}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          立即刷新
        </button>
      </div>

      {errorMessage && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{errorMessage}</div>}

      {isLoading && jobs.length === 0 ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : jobs.length === 0 ? (
        <div className="py-12 text-center text-gray-400">暂无任务</div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">类型</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">状态</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">耗时</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">重试</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">创建时间</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">操作</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <Link href={`/jobs/${job.id}`} className="font-medium text-primary-600 hover:underline">
                        {jobTypeLabels[job.job_type] || job.job_type}
                      </Link>
                    </td>
                    <td className="px-5 py-3"><StatusBadge status={job.status} /></td>
                    <td className="px-5 py-3 text-gray-500">
                      {formatDuration(job.started_at, job.finished_at)}
                    </td>
                    <td className="px-5 py-3 text-gray-500">{job.retry_count}</td>
                    <td className="px-5 py-3 text-gray-400">
                      {new Date(job.created_at).toLocaleString("zh-CN")}
                    </td>
                    <td className="px-5 py-3">
                      {job.status === "failed" && (
                        <button
                          onClick={() => handleRetry(job.id)}
                          className="text-sm text-primary-600 hover:underline"
                        >
                          重试
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
              >
                上一页
              </button>
              <span className="text-sm text-gray-500">{page} / {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
