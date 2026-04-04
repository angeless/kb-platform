"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface Skill {
  id: string;
  stage_name: string;
  name: string;
  description: string | null;
  prompt_template: string;
  version: number;
  is_active: boolean;
  created_at: string;
}

export default function SkillsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get<Skill[]>(`/v1/projects/${projectId}/skills`);
      setSkills(resp.data);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchSkills(); }, [fetchSkills]);

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SKILL 管理</h1>
          <p className="mt-1 text-sm text-gray-500">自定义知识处理规则</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : skills.length === 0 ? (
        <div className="py-12 text-center text-gray-400">
          暂无 SKILL，可通过 API 创建
        </div>
      ) : (
        <div className="grid gap-4">
          {skills.map((skill) => (
            <div key={skill.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{skill.name}</h3>
                  <p className="text-xs text-gray-500">Stage: {skill.stage_name} | v{skill.version}</p>
                </div>
                <span className={`rounded-full px-2 py-1 text-xs ${skill.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                  {skill.is_active ? "激活" : "停用"}
                </span>
              </div>
              {skill.description && (
                <p className="mt-2 text-sm text-gray-600">{skill.description}</p>
              )}
              <pre className="mt-2 max-h-24 overflow-auto rounded bg-gray-50 p-2 text-xs text-gray-700">
                {skill.prompt_template.slice(0, 200)}{skill.prompt_template.length > 200 ? "..." : ""}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
