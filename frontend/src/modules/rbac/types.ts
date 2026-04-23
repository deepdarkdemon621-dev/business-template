export type Scope = "global" | "dept_tree" | "dept" | "own";

export interface Role {
  id: string;
  code: string;
  name: string;
  isBuiltin: boolean;
  isSuperadmin: boolean;
}

export interface RoleListItem extends Role {
  userCount: number;
  permissionCount: number;
  updatedAt: string;
}

export interface RolePermissionItem {
  permissionCode: string;
  scope: Scope;
}

export interface RoleDetail extends Role {
  permissions: RolePermissionItem[];
  userCount: number;
  updatedAt: string;
}

export interface RoleCreatePayload {
  code: string;
  name: string;
  permissions: RolePermissionItem[];
}

export interface RoleUpdatePayload {
  code?: string;
  name?: string;
  permissions?: RolePermissionItem[];
}

export interface RoleDeletedResponse {
  id: string;
  deletedUserRoles: number;
}

export interface Permission {
  id: string;
  code: string;
  resource: string;
  action: string;
  description: string | null;
}
