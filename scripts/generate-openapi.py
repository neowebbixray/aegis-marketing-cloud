#!/usr/bin/env python3
"""
Generate OpenAPI 3.1 specification from the FastAPI application.

Usage:
    python scripts/generate-openapi.py

Outputs:
    docs/openapi.json — OpenAPI 3.1 JSON spec
    docs/openapi.yaml — OpenAPI 3.1 YAML spec (with x-amc-* extensions)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure the project root and backend are on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_BACKEND = _PROJECT_ROOT / "src" / "backend"
sys.path.insert(0, str(_SRC_BACKEND))
sys.path.insert(0, str(_SRC_BACKEND / "app"))

os.environ.setdefault("AMC_ENV_FILE", str(_PROJECT_ROOT / ".env"))


def generate_openapi() -> dict:
    """Create the FastAPI app and dump its OpenAPI schema."""
    from app.main import create_app

    app = create_app()
    return app.openapi()


def add_extensions(schema: dict) -> dict:
    """Post-process the OpenAPI schema to add x-amc-* extensions.

    These extensions provide additional metadata for API documentation
    and security auditing.
    """
    # Add top-level extension
    schema["x-amc-api"] = {
        "name": "Aegis Marketing Cloud API",
        "version": schema.get("info", {}).get("version", "0.1.0"),
        "documentation": "https://docs.aegismc.com/api",
        "support": "https://support.aegismc.com",
    }

    # Add security extensions per path
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue

            # Determine x-amc-auth
            security = details.get("security", [])
            if security:
                x_amc_auth = "required"
            elif method.lower() in ("get", "head", "options") and path in (
                "/health",
                "/",
            ):
                x_amc_auth = "public"
            else:
                # Try to infer from tags or description
                tags = details.get("tags", [])
                description = details.get("description", "") or details.get(
                    "summary", ""
                )
                if "auth" in tags or "auth" in path.lower():
                    # Some auth endpoints may not require auth (login, register)
                    x_amc_auth = "mixed"
                elif description and (
                    "public" in description.lower()
                    or "unauthorized" in description.lower()
                ):
                    x_amc_auth = "public"
                else:
                    x_amc_auth = "optional"

            details["x-amc-auth"] = x_amc_auth

            # Add x-amc-rate-limit hint
            details["x-amc-rate-limit"] = {
                "enabled": True,
                "limit": 100,
                "window_seconds": 60,
            }

            # Add x-amc-changelog if version info exists
            path_parts = path.split("/")
            for part in path_parts:
                if part.startswith("v") and len(part) > 1:
                    details["x-amc-version"] = part[1:]
                    details["x-amc-changelog"] = (
                        f"https://docs.aegismc.com/api/changelog/v{part[1:]}"
                    )
                    break

    return schema


def main() -> None:
    """Run the generation script."""
    docs_dir = _PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    print("Generating OpenAPI schema...")
    schema = generate_openapi()

    # Add custom extensions
    schema = add_extensions(schema)

    # Write JSON
    json_path = docs_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False, default=str)
    print(f"✅ Written: {json_path}")

    # Write YAML
    try:
        import yaml

        yaml_path = docs_dir / "openapi.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                schema,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                Dumper=yaml.SafeDumper,
            )
        print(f"✅ Written: {yaml_path}")
    except ImportError:
        print(
            "⚠️  PyYAML not installed — skipping YAML output. "
            "Install with: pip install pyyaml"
        )

    # Print summary
    path_count = len(schema.get("paths", {}))
    schema_count = len(schema.get("components", {}).get("schemas", {}))
    print(f"\n📊 Summary: {path_count} paths, {schema_count} schemas")
    print("Done.")


if __name__ == "__main__":
    main()
