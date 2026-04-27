export interface RoleSummary {
  id: string;
  code: string;
  name: string;
}

export interface DepartmentSummary {
  id: string;
  name: string;
  path: string;
}

export interface User {
  id: string;
  email: string;
  fullName: string;
  departmentId: string | null;
  isActive: boolean;
  lastLoginAt: string | null;
  mustChangePassword: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface UserDetail extends User {
  roles: RoleSummary[];
  department: DepartmentSummary | null;
}

export interface UserCreatePayload {
  email: string;
  password: string;
  fullName: string;
  departmentId?: string | null;
  mustChangePassword?: boolean;
}

export interface UserUpdatePayload {
  fullName?: string;
  departmentId?: string | null;
  isActive?: boolean;
}
