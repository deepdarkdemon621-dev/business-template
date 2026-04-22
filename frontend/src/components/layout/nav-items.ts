export type NavItem = {
  label: string;
  path: string;
  requiredPermission?: string;
};

export const NAV_ITEMS: NavItem[] = [
  { label: "仪表盘", path: "/" },
  { label: "用户管理", path: "/admin/users", requiredPermission: "user:list" },
  { label: "部门", path: "/admin/departments", requiredPermission: "department:read" },
];
