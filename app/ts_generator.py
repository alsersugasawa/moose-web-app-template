"""
OpenAPI → TypeScript client generator.

Converts a FastAPI OpenAPI 3.x spec into a TypeScript file containing:
  - Interface declarations for every schema in components/schemas
  - Typed async fetch helper functions for every endpoint in paths

Usage:
    from app.ts_generator import generate_typescript_client
    ts_source = generate_typescript_client(openapi_spec_dict)
"""

from datetime import datetime, timezone
from typing import Any


# ─── Type mapping ─────────────────────────────────────────────────────────────

_TYPE_MAP: dict[str, str] = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "object": "Record<string, unknown>",
    "array": "unknown[]",
    "null": "null",
}

_FORMAT_MAP: dict[str, str] = {
    "date-time": "string",   # ISO-8601 dates arrive as strings
    "date": "string",
    "uuid": "string",
    "email": "string",
    "uri": "string",
    "binary": "Blob",
}


def _resolve_type(schema: dict, schemas: dict) -> str:
    """Resolve an OpenAPI schema node to a TypeScript type string."""
    if not schema:
        return "unknown"

    # $ref resolution
    ref = schema.get("$ref", "")
    if ref.startswith("#/components/schemas/"):
        return ref.split("/")[-1]

    # anyOf / oneOf → union
    any_of = schema.get("anyOf") or schema.get("oneOf")
    if any_of:
        parts = [_resolve_type(s, schemas) for s in any_of]
        return " | ".join(parts)

    # allOf (simplified: use first member)
    all_of = schema.get("allOf")
    if all_of:
        return _resolve_type(all_of[0], schemas)

    fmt = schema.get("format", "")
    if fmt in _FORMAT_MAP:
        return _FORMAT_MAP[fmt]

    oa_type = schema.get("type", "")
    if oa_type == "array":
        items = schema.get("items", {})
        inner = _resolve_type(items, schemas)
        return f"{inner}[]"

    return _TYPE_MAP.get(oa_type, "unknown")


def _schema_to_interface(name: str, schema: dict, schemas: dict) -> list[str]:
    """Emit TypeScript interface lines for a single schema."""
    lines: list[str] = []
    description = schema.get("description", "")
    if description:
        lines.append(f"/** {description} */")
    lines.append(f"export interface {name} {{")

    properties: dict = schema.get("properties", {})
    required: set = set(schema.get("required", []))

    for prop_name, prop_schema in properties.items():
        ts_type = _resolve_type(prop_schema, schemas)
        optional = "" if prop_name in required else "?"
        prop_description = prop_schema.get("description", "")
        if prop_description:
            lines.append(f"  /** {prop_description} */")
        lines.append(f"  {prop_name}{optional}: {ts_type};")

    if not properties:
        lines.append("  [key: string]: unknown;")

    lines.append("}")
    lines.append("")
    return lines


def _operation_to_function(path: str, method: str, operation: dict, schemas: dict) -> list[str]:
    """Emit an async TypeScript fetch function for a single endpoint."""
    lines: list[str] = []

    operation_id = operation.get("operationId", "")
    # Build a camelCase function name from the operation ID or path+method
    if operation_id:
        func_name = _to_camel(operation_id)
    else:
        func_name = _to_camel(f"{method}_{path.replace('/', '_').strip('_')}")

    summary = operation.get("summary") or operation.get("description", "")
    if summary:
        lines.append(f"/** {summary} */")

    # Collect path params
    path_params = [p for p in operation.get("parameters", []) if p.get("in") == "path"]
    query_params = [p for p in operation.get("parameters", []) if p.get("in") == "query"]

    # Resolve request body type
    body_schema = None
    body_type = "unknown"
    request_body = operation.get("requestBody", {})
    if request_body:
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        if json_content:
            body_schema = json_content.get("schema", {})
            body_type = _resolve_type(body_schema, schemas)

    # Resolve response type
    responses = operation.get("responses", {})
    response_type = "unknown"
    for status in ("200", "201"):
        resp = responses.get(status, {})
        content = resp.get("content", {})
        json_content = content.get("application/json", {})
        if json_content:
            response_type = _resolve_type(json_content.get("schema", {}), schemas)
            break

    # Build function signature
    args: list[str] = ["token: string"]
    for p in path_params:
        ts_type = _resolve_type(p.get("schema", {}), schemas) or "string"
        args.append(f"{_to_camel(p['name'])}: {ts_type}")
    for p in query_params:
        ts_type = _resolve_type(p.get("schema", {}), schemas) or "string"
        required = p.get("required", False)
        opt = "" if required else "?"
        args.append(f"{_to_camel(p['name'])}{opt}: {ts_type}")
    if body_schema is not None:
        args.append(f"body: {body_type}")

    sig = ", ".join(args)
    lines.append(f"export async function {func_name}({sig}): Promise<{response_type}> {{")

    # Build URL with path param interpolation
    ts_path = path
    for p in path_params:
        ts_path = ts_path.replace("{" + p["name"] + "}", f"${{{_to_camel(p['name'])}}}")

    # Build query string
    if query_params:
        qs_parts = [f"    if ({_to_camel(p['name'])} !== undefined) params.set('{p['name']}', String({_to_camel(p['name'])}));" for p in query_params]
        lines.append("  const params = new URLSearchParams();")
        lines.extend(qs_parts)
        lines.append(f"  const url = `${{API_BASE}}{ts_path}?${{params.toString()}}`;")
    else:
        lines.append(f"  const url = `${{API_BASE}}{ts_path}`;")

    # fetch call
    lines.append(f"  const res = await fetch(url, {{")
    lines.append(f"    method: '{method.upper()}',")
    lines.append(f"    headers: {{")
    lines.append(f"      'Authorization': `Bearer ${{token}}`,")
    if body_schema is not None:
        lines.append(f"      'Content-Type': 'application/json',")
    lines.append(f"    }},")
    if body_schema is not None:
        lines.append(f"    body: JSON.stringify(body),")
    lines.append(f"  }});")
    lines.append(f"  if (!res.ok) {{")
    lines.append(f"    const err = await res.json().catch(() => ({{ detail: res.statusText }}));")
    lines.append(f"    throw new Error(err.detail ?? `HTTP ${{res.status}}`);")
    lines.append(f"  }}")
    lines.append(f"  return res.json() as Promise<{response_type}>;")
    lines.append("}")
    lines.append("")
    return lines


def _to_camel(s: str) -> str:
    """Convert snake_case or kebab-case to camelCase."""
    parts = s.replace("-", "_").split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_typescript_client(spec: dict) -> str:
    """
    Convert a FastAPI OpenAPI 3.x spec dict to a TypeScript source string.

    Returns a complete .ts file containing:
      - Interface declarations for all schemas
      - Async fetch function wrappers for all endpoints
    """
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = spec.get("info", {}).get("title", "API")
    version = spec.get("info", {}).get("version", "")

    lines: list[str] = [
        "// ─────────────────────────────────────────────────────────────────────────────",
        f"// Auto-generated TypeScript client — {title} {version}",
        f"// Generated: {generated_at}",
        "// DO NOT EDIT — regenerate from /api/admin/export/typescript-client",
        "// ─────────────────────────────────────────────────────────────────────────────",
        "",
        "const API_BASE: string = (typeof window !== 'undefined')",
        "  ? window.location.origin",
        "  : 'http://localhost:8080';",
        "",
        "// ─── Types ───────────────────────────────────────────────────────────────────",
        "",
    ]

    schemas: dict[str, Any] = spec.get("components", {}).get("schemas", {})
    for schema_name, schema_obj in schemas.items():
        if schema_obj.get("type") == "object" or "properties" in schema_obj:
            lines.extend(_schema_to_interface(schema_name, schema_obj, schemas))
        elif schema_obj.get("enum"):
            # Emit a TypeScript string union for enums
            values = " | ".join(f'"{v}"' for v in schema_obj["enum"])
            lines.append(f"export type {schema_name} = {values};")
            lines.append("")

    lines += [
        "// ─── API Functions ───────────────────────────────────────────────────────────",
        "",
    ]

    paths: dict = spec.get("paths", {})
    for path, path_item in paths.items():
        for method in ("get", "post", "put", "patch", "delete"):
            operation: dict = path_item.get(method, {})
            if not operation:
                continue
            # Skip endpoints that are just file downloads
            responses = operation.get("responses", {})
            is_download = any(
                "application/octet-stream" in (r.get("content") or {})
                for r in responses.values()
            )
            if is_download:
                continue
            lines.extend(_operation_to_function(path, method, operation, schemas))

    return "\n".join(lines)
