import Ajv from "ajv";
import addFormats from "ajv-formats";
import { registerRuleKeywords } from "./form-rules";

export const ajv = new Ajv({
  allErrors: true,
  strictSchema: false,
  useDefaults: true,
});

addFormats(ajv);
registerRuleKeywords(ajv);
