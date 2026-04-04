"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface CostSummary {
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
}

export default function CostDashboardPage() {
  const [costs, setCosts] = useState<CostSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchCosts = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get<CostSummary[]>("/v1/admin/cost-summary");
      setCosts(resp.data);
    } catch (e) {
      setError("加载成本数据失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCosts(); }, [fetchCosts]);

  const totalCost = costs.reduce((sum, c) => sum + c.cost_usd, 0);
  const totalTokens = costs.reduce((sum, c) => sum + c.prompt_tokens + c.completion_tokens, 0);

  return (
    <div>
      <div className="mb-4">
        <Link href="/admin/audit-logs" className="text-sm text-primary-600 hover:underline">
          ← 管理面板
        </Link>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">模型成本看板</h1>

      {/* Summary cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-gray-400">今日总费用</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">${totalCost.toFixed(4)}</div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-gray-400">今日总 Token</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{totalTokens.toLocaleString()}</div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-gray-400">活跃模型数</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{costs.length}</div>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {/* Per-model table */}
      {loading ? (
        <div className="py-8 text-center text-gray-400">加载中...</div>
      ) : costs.length === 0 ? (
        <div className="py-8 text-center text-gray-400">暂无消耗数据</div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-600">模型</th>
                <th className="px-5 py-3 text-right font-medium text-gray-600">Prompt Tokens</th>
                <th className="px-5 py-3 text-right font-medium text-gray-600">Completion Tokens</th>
                <th className="px-5 py-3 text-right font-medium text-gray-600">费用 (USD)</th>
              </tr>
            </thead>
            <tbody>
              {costs.map((c) => (
                <tr key={c.model} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-800">{c.model}</td>
                  <td className="px-5 py-3 text-right text-gray-500">{c.prompt_tokens.toLocaleString()}</td>
                  <td className="px-5 py-3 text-right text-gray-500">{c.completion_tokens.toLocaleString()}</td>
                  <td className="px-5 py-3 text-right font-medium text-gray-900">${c.cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
