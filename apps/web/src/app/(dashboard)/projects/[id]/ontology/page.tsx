"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface Concept {
  id: string;
  name: string;
  definition: string | null;
  concept_type: string;
  parent_id: string | null;
}

interface Relation {
  id: string;
  source_concept_id: string;
  target_concept_id: string;
  relation_type: string;
  confidence: number | null;
}

export default function OntologyPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [cResp, rResp] = await Promise.all([
        api.get<Concept[]>(`/v1/projects/${projectId}/ontology/concepts`),
        api.get<Relation[]>(`/v1/projects/${projectId}/ontology/relations`),
      ]);
      setConcepts(cResp.data);
      setRelations(rResp.data);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const conceptMap = Object.fromEntries(concepts.map(c => [c.id, c]));
  const rootConcepts = concepts.filter(c => !c.parent_id);
  const children = (parentId: string) => concepts.filter(c => c.parent_id === parentId);

  const ConceptNode = ({ concept, depth = 0 }: { concept: Concept; depth?: number }) => (
    <div style={{ marginLeft: depth * 20 }} className="mb-1">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-800">{concept.name}</span>
        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">{concept.concept_type}</span>
      </div>
      {concept.definition && (
        <p className="ml-4 text-xs text-gray-500">{concept.definition}</p>
      )}
      {children(concept.id).map(child => (
        <ConceptNode key={child.id} concept={child} depth={depth + 1} />
      ))}
    </div>
  );

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">知识本体</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {loading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : concepts.length === 0 ? (
        <div className="py-12 text-center text-gray-400">暂无本体数据，请运行 AI 提取</div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Concept Tree */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-gray-700">概念层级</h2>
            {rootConcepts.map(c => <ConceptNode key={c.id} concept={c} />)}
          </div>

          {/* Relations */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-gray-700">关系 ({relations.length})</h2>
            <div className="space-y-2">
              {relations.slice(0, 50).map(r => (
                <div key={r.id} className="flex items-center gap-2 text-sm">
                  <span className="font-medium text-gray-800">
                    {conceptMap[r.source_concept_id]?.name || r.source_concept_id.slice(0, 8)}
                  </span>
                  <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">{r.relation_type}</span>
                  <span className="font-medium text-gray-800">
                    {conceptMap[r.target_concept_id]?.name || r.target_concept_id.slice(0, 8)}
                  </span>
                  {r.confidence && (
                    <span className="text-xs text-gray-400">{(r.confidence * 100).toFixed(0)}%</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
