"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface JobDetail {
  id: string;
  project_id: string;
  job_type: string;
  status: string;
  error_message: string | null;
  retry_count: number;
  celery_task_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

const jobTypeLabels: Record<string, string> = {
  ingest: "资料解析",
  classify: "内容分类",
  architecture_draft: "架构生成",
  kb_generate: "文档生成",
  review_publish: "审核发布",
};

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;

  const [job, setJob] = useState<JobDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);

  const fetchJob = async () => {
    try {
      const resp = await api.get<JobDetail>(`/v1/jobs/${jobId}`);
      setJob(resp.data);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJob();
    const interval = setInterval(fetchJob, 5000);
    return () => clearInterval(interval);
  }, [jobId]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await api.post(`/v1/jobs/${jobId}/retry`, {});
      fetchJob();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "重试失败");
    } finally {
      setRetrying(false);
    }
  };

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;
  if (error || !job) return <div className="py-12 text-center text-red-500">{error}</div>;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">
              {jobTypeLabels[job.job_type] || job.job_type}
            </h1>
            <StatusBadge status={job.status} />
          </div>
          <p className="mt-1 text-sm text-gray-400">ID: {job.id}</p>
        </div>
        {job.status === "failed" && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {retrying ? "重试中..." : "重试任务"}
          </button>
        )}
      </div>

      <div className="space-y-4">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-semibold text-gray-900">任务信息</h2>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-gray-500">创建时间</dt>
              <dd className="mt-0.5 text-gray-900">{new Date(job.created_at).toLocaleString("zh-CN")}</dd>
            </div>
            <div>
              <dt className="text-gray-500">开始时间</dt>
              <dd className="mt-0.5 text-gray-900">{job.started_at ? new Date(job.started_at).toLocaleString("zh-CN") : "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">完成时间</dt>
              <dd className="mt-0.5 text-gray-900">{job.finished_at ? new Date(job.finished_at).toLocaleString("zh-CN") : "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">重试次数</dt>
              <dd className="mt-0.5 text-gray-900">{job.retry_count}</dd>
            </div>
            {job.celery_task_id && (
              <div className="col-span-2">
                <dt className="text-gray-500">Celery Task ID</dt>
                <dd className="mt-0.5 font-mono text-xs text-gray-700">{job.celery_task_id}</dd>
              </div>
            )}
          </dl>
        </div>

        {job.error_message && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-5">
            <h2 className="mb-2 font-semibold text-red-700">错误信息</h2>
            <pre className="whitespace-pre-wrap text-sm text-red-600">{job.error_message}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
