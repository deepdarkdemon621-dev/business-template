import { client } from "@/api/client";
import type { Page, PageQuery } from "@/lib/pagination";
import type {
  Department,
  DepartmentCreatePayload,
  DepartmentMovePayload,
  DepartmentNode,
  DepartmentUpdatePayload,
} from "./types";

export async function listDepartments(
  pq: PageQuery & { is_active?: boolean },
): Promise<Page<Department>> {
  const { data } = await client.get<Page<Department>>("/departments", {
    params: pq,
  });
  return data;
}

export async function getDepartmentTree(
  includeInactive = false,
): Promise<DepartmentNode[]> {
  const { data } = await client.get<DepartmentNode[]>("/departments/tree", {
    params: { includeInactive },
  });
  return data;
}

export async function getDepartment(id: string): Promise<Department> {
  const { data } = await client.get<Department>(`/departments/${id}`);
  return data;
}

export async function createDepartment(
  payload: DepartmentCreatePayload,
): Promise<Department> {
  const { data } = await client.post<Department>("/departments", payload);
  return data;
}

export async function updateDepartment(
  id: string,
  payload: DepartmentUpdatePayload,
): Promise<Department> {
  const { data } = await client.patch<Department>(`/departments/${id}`, payload);
  return data;
}

export async function moveDepartment(
  id: string,
  payload: DepartmentMovePayload,
): Promise<Department> {
  const { data } = await client.post<Department>(
    `/departments/${id}/move`,
    payload,
  );
  return data;
}

export async function softDeleteDepartment(id: string): Promise<void> {
  await client.delete(`/departments/${id}`);
}
