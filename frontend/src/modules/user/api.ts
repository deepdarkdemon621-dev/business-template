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
  const { data } = await client.get<Page<User>>("/users", { params: pq });
  return data;
}

export async function getUser(id: string): Promise<UserDetail> {
  const { data } = await client.get<UserDetail>(`/users/${id}`);
  return data;
}

export async function createUser(payload: UserCreatePayload): Promise<User> {
  const { data } = await client.post<User>("/users", payload);
  return data;
}

export async function updateUser(id: string, payload: UserUpdatePayload): Promise<User> {
  const { data } = await client.patch<User>(`/users/${id}`, payload);
  return data;
}

export async function softDeleteUser(id: string): Promise<void> {
  await client.delete(`/users/${id}`);
}

export async function assignRole(userId: string, roleId: string): Promise<void> {
  await client.post(`/users/${userId}/roles/${roleId}`);
}

export async function revokeRole(userId: string, roleId: string): Promise<void> {
  await client.delete(`/users/${userId}/roles/${roleId}`);
}

export async function listRoles(): Promise<RoleSummary[]> {
  const { data } = await client.get<Page<RoleSummary>>("/roles", {
    params: { size: 100 },
  });
  return data.items;
}
