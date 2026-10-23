import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { ApiErrorBody } from "@/types";

export const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  // Backend CSRF himoyasi shu sarlavhani talab qiladi
  headers: { "X-Requested-With": "csw" },
  timeout: 60_000,
});

let refreshing: Promise<void> | null = null;

// Access token muddati tugasa (15 daqiqa) — bir marta refresh qilib, so'rovni qaytaramiz
api.interceptors.response.use(undefined, async (error: AxiosError<ApiErrorBody>) => {
  const cfg = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
  const isAuthCall = cfg?.url?.startsWith("/auth/");
  if (error.response?.status === 401 && cfg && !cfg._retried && !isAuthCall) {
    cfg._retried = true;
    refreshing ??= api.post("/auth/refresh").then(() => undefined).finally(() => (refreshing = null));
    try {
      await refreshing;
      return api(cfg);
    } catch {
      window.dispatchEvent(new Event("csw:logout"));
    }
  }
  return Promise.reject(error);
});

/** Backend xatosidan barqaror kodni oladi (tarjima uchun). */
export function errorCode(e: unknown): string {
  const ax = e as AxiosError<ApiErrorBody>;
  if (!ax.response) return "network";
  return ax.response.data?.error?.code ?? (ax.response.status === 422 ? "validation" : "unknown");
}

export function errorMessage(e: unknown): string | undefined {
  return (e as AxiosError<ApiErrorBody>).response?.data?.error?.message;
}
