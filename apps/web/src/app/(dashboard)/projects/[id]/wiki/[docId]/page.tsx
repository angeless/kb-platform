"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { MarkdownView } from "@/components/markdown-view";
import { WikiToc } from "@/components/wiki-toc";
import { WikiBreadcrumb } from "@/components/wiki-breadcrumb";
import { SourceRefs } from "@/components/source-refs";
import { useWikiScrollRef } from "@/components/wiki-scroll-context";

interface SourceRef {
  id: string;
  asset_chunk_id: string;
  location_hint: string | null;
}

interface DocVersion {
  version: number;
  content_md: string;
  source_refs: SourceRef[];
}

interface DocDetail {
  id: string;
  project_id: string;
  node_id: string | null;
  title: string;
  doc_type: string;
  current_version: number;
  status: string;
  versions: DocVersion[];
}

interface ArchNode {
  id: string;
  node_name: string;
  parent_id: string | null;
}

interface SearchHit {
  doc_id: string;
  title: string;
  score: number;
}

interface CrossRef {
  id: string;
  source_doc_id: string;
  target_doc_id: string;
  relation_type: string;
  confidence: number;
  source_title: string | null;
  target_title: string | null;
  target_project_id: string | null;
  target_project_name: string | null;
}

const RELATION_LABELS: Record<string, string> = {
  related: "相关",
  depends_on: "依赖",
  extends: "扩展",
  contradicts: "矛盾",
  supersedes: "替代",
};

export default function WikiDocPage() {
  const params = useParams();
  const projectId = params.id as string;
  const docId = params.docId as string;
  const contentRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useWikiScrollRef();

  const [doc, setDoc] = useState<DocDetail | null>(null);
  const [nodes, setNodes] = useState<ArchNode[]>([]);
  const [related, setRelated] = useState<SearchHit[]>([]);
  const [crossRefs, setCrossRefs] = useState<CrossRef[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const docResp = await api.get<DocDetail>(`/v1/docs/${docId}`);
        setDoc(docResp.data);

        // Load architecture nodes for breadcrumb
        const archResp = await api.get<{ id: string }[]>(
          `/v1/projects/${projectId}/architectures`,
        );
        if (archResp.data.length > 0) {
          const nodesResp = await api.get<ArchNode[]>(
            `/v1/architectures/${archResp.data[0].id}/nodes`,
          );
          setNodes(nodesResp.data);
        }

        // Load related docs + cross refs (non-critical)
        try {
          const searchResp = await api.post<SearchHit[]>(
            "/v1/search/hybrid",
            { project_id: projectId, query: docResp.data.title, page_size: 6 },
          );
          setRelated(searchResp.data.filter((h) => h.doc_id !== docId).slice(0, 5));
        } catch {
          // Related docs is non-critical
        }

        try {
          const refsResp = await api.get<CrossRef[]>(`/v1/cross-refs/doc/${docId}`);
          setCrossRefs(refsResp.data);
        } catch {
          // Cross refs is non-critical
        }
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [projectId, docId]);

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;
  if (error || !doc) return <div className="py-12 text-center text-red-500">{error || "文档不存在"}</div>;

  const currentVer = doc.versions.find((v) => v.version === doc.current_version);

  return (
    <div className="flex gap-6 px-6 py-6">
      {/* Main content */}
      <article className="min-w-0 flex-1">
        <WikiBreadcrumb nodes={nodes} nodeId={doc.node_id} projectId={projectId} />

        <h1 className="mb-4 text-2xl font-bold text-gray-900">{doc.title}</h1>
        <div className="mb-6 flex gap-3 text-xs text-gray-400">
          <span>{doc.doc_type}</span>
          <span>v{doc.current_version}</span>
          <span className="capitalize">{doc.status}</span>
        </div>

        <div ref={contentRef} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          {currentVer ? (
            <MarkdownView content={currentVer.content_md} />
          ) : (
            <p className="text-gray-400">暂无内容</p>
          )}
        </div>

        {/* Source refs */}
        {currentVer && currentVer.source_refs.length > 0 && (
          <SourceRefs refs={currentVer.source_refs} />
        )}

        {/* Related docs */}
        {related.length > 0 && (
          <section className="mt-8">
            <h2 className="mb-3 text-lg font-semibold text-gray-800">相关知识</h2>
            <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
              {related.map((hit) => (
                <li key={hit.doc_id}>
                  <Link
                    href={`/projects/${projectId}/wiki/${hit.doc_id}`}
                    className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
                  >
                    <span className="text-sm text-gray-700">{hit.title}</span>
                    <span className="text-xs text-gray-400">
                      {Math.round(hit.score * 100)}% 相关
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Cross-references */}
        {crossRefs.length > 0 && (
          <section className="mt-8">
            <h2 className="mb-3 text-lg font-semibold text-gray-800">关联文档</h2>
            <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
              {crossRefs.map((ref) => {
                const isSource = ref.source_doc_id === docId;
                const linkedDocId = isSource ? ref.target_doc_id : ref.source_doc_id;
                const linkedTitle = isSource ? ref.target_title : ref.source_title;
                const isCrossProject = ref.target_project_id && ref.target_project_id !== projectId;
                return (
                  <li key={ref.id}>
                    <Link
                      href={isCrossProject
                        ? `/projects/${ref.target_project_id}/wiki/${linkedDocId}`
                        : `/projects/${projectId}/wiki/${linkedDocId}`
                      }
                      className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
                    >
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                          {RELATION_LABELS[ref.relation_type] || ref.relation_type}
                        </span>
                        <span className="text-sm text-gray-700">{linkedTitle}</span>
                        {isCrossProject && (
                          <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">
                            {ref.target_project_name}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-gray-400">
                        {Math.round(ref.confidence * 100)}%
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </article>

      {/* TOC sidebar — hidden on mobile and tablet */}
      <aside className="hidden w-56 shrink-0 xl:block">
        <div className="sticky top-6">
          <WikiToc contentRef={contentRef} scrollContainerRef={scrollContainerRef ?? undefined} />
        </div>
      </aside>
    </div>
  );
}
