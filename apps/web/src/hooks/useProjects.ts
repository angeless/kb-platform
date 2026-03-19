import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Project {
  id: string;
  name: string;
  industry_hint: string | null;
  status: string;
  created_at: string;
}

interface ProjectsResponse {
  data: Project[];
  meta?: { total?: number };
}

export function useProjects(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ["projects", page, pageSize],
    queryFn: async () => {
      const resp = await api.get<Project[]>(
        `/v1/projects?page=${page}&page_size=${pageSize}`,
      );
      return { data: resp.data, total: resp.meta?.total ?? resp.data.length };
    },
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: { name: string; industry_hint?: string | null }) =>
      api.post<Project>("/v1/projects", params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
