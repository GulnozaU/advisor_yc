import { useCallback } from "react";
import axios from "axios";
import { useAuth } from "@clerk/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function useApi() {
  const { getToken } = useAuth();
  return useCallback(
    async (method, path, data) => {
      const token = await getToken();
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios({ method, url: `${API}${path}`, data, headers, withCredentials: true });
      return res.data;
    },
    [getToken],
  );
}

export const errorText = (e) => e?.response?.data?.detail || e?.message || "Something went wrong.";

export const isGuest = () => localStorage.getItem("aoc_guest") === "1";

export async function startGuest() {
  await axios.post(`${API}/guest/start`, {}, { withCredentials: true });
  localStorage.setItem("aoc_guest", "1");
}

export async function endGuest() {
  localStorage.removeItem("aoc_guest");
  await axios.post(`${API}/guest/end`, {}, { withCredentials: true }).catch(() => {});
}

export function useMe() {
  const api = useApi();
  return useQuery({ queryKey: ["me"], queryFn: () => api("get", "/me") });
}

export function usePriorities(status = "open") {
  const api = useApi();
  return useQuery({ queryKey: ["priorities", status], queryFn: () => api("get", `/priorities?status=${status}`) });
}

export function useCalls() {
  const api = useApi();
  return useQuery({ queryKey: ["calls"], queryFn: () => api("get", "/calls") });
}

export function useApiMutation(method, pathFn, invalidate = ["priorities"]) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars) => api(method, typeof pathFn === "function" ? pathFn(vars) : pathFn, vars?.body ?? vars),
    onSuccess: () => invalidate.forEach((k) => qc.invalidateQueries({ queryKey: [k] })),
  });
}
