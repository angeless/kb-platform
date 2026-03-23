"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { MarkdownView } from "@/components/markdown-view";
import { WikiToc } from "@/components/wiki-toc";
import { WikiBreadcrumb } from "@/components/wiki-breadcrumb";
import { SourceRefs } from "@/components/source-refs";

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

export default function WikiDocPage() {
  const params = useParams();
  const projectId = params.id as string;
  const docId = params.docId as string;
  const contentRef = useRef<HTMLDivElement>(null);

  const [doc, setDoc] = useState<DocDetail | null>(null);
  const [nodes, setNodes] = useState<ArchNode[]>([]);
  const [related, setRelated] = useState<SearchHit[]>([]);
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

        // Load related docs via search using doc title
        try {
          const searchResp = await api.get<SearchHit[]>(
            `/v1/search/hybrid?project_id=${projectId}&query=${encodeURIComponent(docResp.data.title)}&page_size=6`,
          );
          setRelated(searchResp.data.filter((h) => h.doc_id !== docId).slice(0, 5));
        } catch {
          // Related docs is non-critical
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
  if (error || !doc) return <div className="py-12 text-center text-red-500">{error}</div>;

  const currentVer = doc.versions.find((v) => v.version === doc.current_version);

  return (
    <div className="flex gap-6 px-4 py-6">
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
      </article>

      {/* TOC sidebar — hidden on mobile */}
      <aside className="hidden w-56 shrink-0 lg:block">
        <div className="sticky top-6">
          <WikiToc contentRef={contentRef} />
        </div>
      </aside>
    </div>
  );
}
