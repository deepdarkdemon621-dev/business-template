export const roleCreateSchema = {
  type: "object",
  required: ["code", "name"],
  properties: {
    code: {
      type: "string",
      title: "Code",
      minLength: 2,
      maxLength: 50,
      pattern: "^[a-z][a-z0-9_]*$",
    },
    name: {
      type: "string",
      title: "Name",
      minLength: 1,
      maxLength: 100,
    },
  },
} as const;

export const roleUpdateSchema = {
  type: "object",
  properties: {
    code: {
      type: "string",
      title: "Code",
      minLength: 2,
      maxLength: 50,
      pattern: "^[a-z][a-z0-9_]*$",
    },
    name: {
      type: "string",
      title: "Name",
      minLength: 1,
      maxLength: 100,
    },
  },
} as const;
