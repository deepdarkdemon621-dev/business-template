import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { isProblemDetails } from "@/lib/problem-details";
import { getToken } from "@/lib/auth/storage";

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// ── Request interceptor ────────────────────────────────────────────────────
// Attach the in-memory/sessionStorage access token as a Bearer header.
client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── 401 refresh queue ──────────────────────────────────────────────────────
let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null) => void> = [];

function onRefreshed(token: string | null): void {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

// Wired by AuthProvider after it mounts so there is no circular import.
export let refreshTokenFn: (() => Promise<string | null>) | null = null;

export function setRefreshTokenFn(fn: () => Promise<string | null>): void {
  refreshTokenFn = fn;
}

// Extend InternalAxiosRequestConfig to track retry attempts.
interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

// ── Response interceptor ───────────────────────────────────────────────────
client.interceptors.response.use(
  (response) => response,
  async (err: AxiosError) => {
    const originalRequest = err.config as RetryableConfig | undefined;

    // 401 handling: attempt token refresh then retry, or queue if already refreshing.
    // Skip auth endpoints: /auth/refresh (recursive), /auth/login (bad creds, not expired token).
    const isAuthEndpoint =
      originalRequest?.url?.endsWith("/auth/refresh") ||
      originalRequest?.url?.endsWith("/auth/login");
    if (
      err.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isAuthEndpoint &&
      refreshTokenFn
    ) {
      originalRequest._retry = true;

      if (!isRefreshing) {
        isRefreshing = true;
        const newToken = await refreshTokenFn();
        isRefreshing = false;
        onRefreshed(newToken);

        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return client(originalRequest);
        }
        return Promise.reject(err);
      }

      // A refresh is already in flight — queue this request.
      return new Promise((resolve, reject) => {
        refreshSubscribers.push((token) => {
          if (token && originalRequest) {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(client(originalRequest));
          } else {
            reject(err);
          }
        });
      });
    }

    // Unwrap RFC 9457 Problem Details so business code works with the typed object.
    const data = err.response?.data;
    if (isProblemDetails(data)) {
      return Promise.reject(data);
    }

    return Promise.reject(err);
  },
);
