"""Pydantic request/response schemas.

Rules (see 01-schema-validation + 05-api-contract):
- Use Field(max_length=..., ge=..., pattern=...) for field-level rules.
- Use `json_schema_extra={"x-rules": [...]}` for cross-field (FormRuleRegistry).
- Response schemas MUST strip sensitive fields (no password_hash, no raw tokens).
- alias_generator=to_camel + populate_by_name=True on model_config.
"""
