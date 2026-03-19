import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Job {
  id: string;
  job_type: string;
  status: string;
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export function useJobs(projectId: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["jobs", projectId, page, pageSize],
    queryFn: async () => {
      const resp = await api.get<Job[]>(
        `/v1/jobs?project_id=${projectId}&page=${page}&page_size=${pageSize}`,
      );
      return { data: resp.data, total: resp.meta?.total ?? 0 };
    },
    enabled: !!projectId,
    refetchInterval: 10_000, // Auto-refresh every 10s for running jobs
  });
}

export function useRetryJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobId: string) => api.post(`/v1/jobs/${jobId}/retry`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
