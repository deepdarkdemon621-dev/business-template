import { client } from "@/api/client";
import type { Page, PageQuery } from "@/lib/pagination";
import type {
  Permission,
  RoleCreatePayload,
  RoleDeletedResponse,
  RoleDetail,
  RoleListItem,
  RoleUpdatePayload,
} from "./types";

export async function listRoles(pq: PageQuery): Promise<Page<RoleListItem>> {
  const { data } = await client.get<Page<RoleListItem>>("/roles", { params: pq });
  return data;
}

export async function getRole(id: string): Promise<RoleDetail> {
  const { data } = await client.get<RoleDetail>(`/roles/${id}`);
  return data;
}

export async function createRole(payload: RoleCreatePayload): Promise<RoleDetail> {
  const { data } = await client.post<RoleDetail>("/roles", payload);
  return data;
}

export async function updateRole(
  id: string,
  payload: RoleUpdatePayload,
): Promise<RoleDetail> {
  const { data } = await client.patch<RoleDetail>(`/roles/${id}`, payload);
  return data;
}

export async function deleteRole(id: string): Promise<RoleDeletedResponse> {
  const { data } = await client.delete<RoleDeletedResponse>(`/roles/${id}`);
  return data;
}

export async function listPermissions(): Promise<Permission[]> {
  // Fetch size=100 to get all perms in one call (total is ~20 post-0006).
  const { data } = await client.get<Page<Permission>>("/permissions", {
    params: { page: 1, size: 100 },
  });
  return data.items;
}
