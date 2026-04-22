export interface Department {
  id: string;
  parentId: string | null;
  name: string;
  path: string;
  depth: number;
  isActive: boolean;
}

export interface DepartmentNode extends Department {
  children: DepartmentNode[];
}

export interface DepartmentCreatePayload {
  name: string;
  parentId: string;
}

export interface DepartmentUpdatePayload {
  name: string;
}

export interface DepartmentMovePayload {
  newParentId: string;
}
