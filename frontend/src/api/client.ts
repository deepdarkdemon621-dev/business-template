import axios, { AxiosError } from "axios";
import { isProblemDetails } from "@/lib/problem-details";

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  headers: { "Content-Type": "application/json" },
});

client.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    const data = err.response?.data;
    if (isProblemDetails(data)) {
      return Promise.reject(data);
    }
    return Promise.reject(err);
  },
);
