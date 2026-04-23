export const userCreateSchema = {
  type: "object",
  properties: {
    email: { type: "string", title: "邮箱", format: "email", maxLength: 254 },
    fullName: { type: "string", title: "姓名", minLength: 1, maxLength: 100 },
    password: { type: "string", title: "密码", "x-inputType": "password" },
  },
  required: ["email", "fullName", "password"],
  passwordPolicy: { field: "password" },
} as const;

export const userUpdateSchema = {
  type: "object",
  properties: {
    fullName: { type: "string", title: "姓名", minLength: 1, maxLength: 100 },
  },
  required: ["fullName"],
} as const;
