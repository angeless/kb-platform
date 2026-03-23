"use client";

interface SourceRef {
  id: string;
  asset_chunk_id: string;
  location_hint: string | null;
}

interface SourceRefsProps {
  refs: SourceRef[];
}

export function SourceRefs({ refs }: SourceRefsProps) {
  if (refs.length === 0) return null;

  return (
    <section className="mt-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">来源追溯</h3>
      <ul className="space-y-2">
        {refs.map((ref, i) => (
          <li key={ref.id} className="flex items-start gap-2 text-xs text-gray-500">
            <span className="mt-0.5 shrink-0 rounded bg-gray-100 px-1.5 py-0.5 font-mono text-gray-400">
              [{i + 1}]
            </span>
            <div>
              <span className="font-mono text-gray-600">
                {ref.asset_chunk_id.slice(0, 12)}...
              </span>
              {ref.location_hint && (
                <span className="ml-2 text-gray-400">{ref.location_hint}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
