import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Profile } from "../lib/api";

export function useProfile() {
  return useQuery<Profile>({
    queryKey: ["profile"],
    queryFn: () => api.profile.get(),
    staleTime: 5 * 60 * 1000, // 5 min
    retry: 1,
  });
}

export function useUpsertProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fields: Partial<Profile>) => api.profile.upsert(fields),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });
}
