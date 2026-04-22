export const departmentCreateSchema = {
  type: "object",
  properties: {
    name: {
      type: "string",
      title: "部门名称",
      minLength: 1,
      maxLength: 100,
    },
  },
  required: ["name"],
};

export const departmentUpdateSchema = departmentCreateSchema;
