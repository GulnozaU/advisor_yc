import { useQuery } from "@tanstack/react-query";
import { useApi } from "@/lib/api";

export function useAdvisor() {
  const api = useApi();
  return useQuery({ queryKey: ["advisor"], queryFn: () => api("get", "/advisor/items") });
}

export function useGoogleStatus(enabled) {
  const api = useApi();
  return useQuery({ queryKey: ["google"], queryFn: () => api("get", "/advisor/google/status"), enabled, retry: false });
}

export function useCompetitors() {
  const api = useApi();
  return useQuery({ queryKey: ["competitors"], queryFn: () => api("get", "/advisor/competitors") });
}
