import { client } from "@/api/client";
import type { Page, PageQuery } from "@/lib/pagination";
import type {
  RoleSummary,
  User,
  UserCreatePayload,
  UserDetail,
  UserUpdatePayload,
} from "./types";

export async function listUsers(
  pq: PageQuery & { is_active?: boolean }
): Promise<Page<User>> {
  const { data } = await client.get<Page<User>>("/api/v1/users", { params: pq });
  return data;
}

export async function getUser(id: string): Promise<UserDetail> {
  const { data } = await client.get<UserDetail>(`/api/v1/users/${id}`);
  return data;
}

export async function createUser(payload: UserCreatePayload): Promise<User> {
  const { data } = await client.post<User>("/api/v1/users", payload);
  return data;
}

export async function updateUser(id: string, payload: UserUpdatePayload): Promise<User> {
  const { data } = await client.patch<User>(`/api/v1/users/${id}`, payload);
  return data;
}

export async function softDeleteUser(id: string): Promise<void> {
  await client.delete(`/api/v1/users/${id}`);
}

export async function assignRole(userId: string, roleId: string): Promise<void> {
  await client.post(`/api/v1/users/${userId}/roles/${roleId}`);
}

export async function revokeRole(userId: string, roleId: string): Promise<void> {
  await client.delete(`/api/v1/users/${userId}/roles/${roleId}`);
}

export async function listRoles(): Promise<RoleSummary[]> {
  const { data } = await client.get<Page<RoleSummary>>("/api/v1/roles", {
    params: { size: 100 },
  });
  return data.items;
}
