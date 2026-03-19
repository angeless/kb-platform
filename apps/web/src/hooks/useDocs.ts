import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Doc {
  id: string;
  title: string;
  doc_type: string;
  status: string;
  current_version: number;
  node_id: string | null;
  created_at: string;
}

export function useDocs(projectId: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["docs", projectId, page, pageSize],
    queryFn: async () => {
      const resp = await api.get<Doc[]>(
        `/v1/docs?project_id=${projectId}&page=${page}&page_size=${pageSize}`,
      );
      return { data: resp.data, total: resp.meta?.total ?? 0 };
    },
    enabled: !!projectId,
  });
}
