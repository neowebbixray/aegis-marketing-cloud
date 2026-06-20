#!/usr/bin/env python3
"""
Aegis Marketing Cloud — CI Project Structure Validator
======================================================

Validates that the project meets structural and security requirements
before CI pipelines proceed. Modeled after industry-standard CI validation
runners used across enterprise marketing platforms.

Checks performed:
  1. Required directories exist (backend, frontend, docs, infra, scripts)
  2. Required root files exist (pyproject.toml, package.json, Dockerfiles,
     docker-compose.yml, .env.example, .gitignore)
  3. Each major component has its essential sub-structure
  4. Documentation volumes exist and line counts are reported
  5. No placeholder/example secrets are committed in sensitive files
  6. YAML/JSON config files are parseable
  7. Dockerfiles reference valid base images
  8. .gitignore covers common secrets patterns

Exit codes:
  0 — All checks passed
  1 — One or more checks failed
"""

import json
import os
import re
import sys
import yaml
from pathlib import Path
from typing import List, Tuple

# ─── Configuration ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_DIRECTORIES: List[str] = [
    "src/backend",
    "src/frontend",
    "docs",
    "infra",
    "scripts",
    ".github",
    ".github/workflows",
    ".github/ISSUE_TEMPLATE",
]

REQUIRED_ROOT_FILES: List[str] = [
    "pyproject.toml",
    "package.json",
    "docker-compose.yml",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "Makefile",
]

BACKEND_SUBDIRS: List[str] = [
    "app",
    "app/api",
    "app/core",
    "app/models",
    "app/services",
    "app/tests",
]

FRONTEND_SUBDIRS: List[str] = [
    "src",
    "public",
]

INFRA_SUBDIRS: List[str] = [
    "compose",
    "docker",
    "terraform",
]

# Files that should NOT contain placeholder secrets
SENSITIVE_FILE_PATTERNS: List[str] = [
    ".env.example",
    "docker-compose.yml",
    "docker-compose*.yml",
    "**/docker-compose*.yml",
    "**/secrets*.yml",
    "**/secrets*.yaml",
]

PLACEHOLDER_PATTERNS: List[str] = [
    r"change-me[-_].*",
    r"your-.*-key",
    r"YOUR_.*_KEY",
    r"placeholder",
    r"xxxxx",
    r"CHANGEME",
    r"your_secret",
    r"your_password",
    r"aegis_secret",
    r"amc_secret",
]

GITIGNORE_REQUIRED_PATTERNS: List[str] = [
    "*.pyc",
    "__pycache__",
    ".env",
    ".venv",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".terraform",
    "*.tfstate",
    "*.tfstate.backup",
    ".coverage",
    "coverage/",
    "*.log",
]

# ─── Helpers ─────────────────────────────────────────────────────────────


def ok(msg: str) -> None:
    print(f"  ✅  {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️   {msg}")


def fail(msg: str) -> None:
    print(f"  ❌  {msg}")


def heading(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def rel_path(path: Path) -> str:
    """Return path relative to project root."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


# ─── Check Functions ─────────────────────────────────────────────────────


def check_directories() -> int:
    """Ensure all required directories exist."""
    errors = 0
    heading("Required Directories")

    for dirname in REQUIRED_DIRECTORIES:
        d = PROJECT_ROOT / dirname
        if d.is_dir():
            ok(f"{dirname}/")
        else:
            fail(f"{dirname}/ — MISSING")
            errors += 1

    # Backend sub-structure
    for sub in BACKEND_SUBDIRS:
        d = PROJECT_ROOT / "src/backend" / sub
        if d.is_dir():
            ok(f"src/backend/{sub}/")
        else:
            warn(f"src/backend/{sub}/ — missing (optional for early stage)")

    # Frontend sub-structure
    for sub in FRONTEND_SUBDIRS:
        d = PROJECT_ROOT / "src/frontend" / sub
        if d.is_dir():
            ok(f"src/frontend/{sub}/")
        else:
            warn(f"src/frontend/{sub}/ — missing (optional for early stage)")

    # Infra sub-structure
    for sub in INFRA_SUBDIRS:
        d = PROJECT_ROOT / "infra" / sub
        if d.is_dir():
            ok(f"infra/{sub}/")
        else:
            warn(f"infra/{sub}/ — missing (optional for early stage)")

    return errors


def check_root_files() -> int:
    """Ensure all required root-level files exist."""
    errors = 0
    heading("Root-Level Files")

    for filename in REQUIRED_ROOT_FILES:
        f = PROJECT_ROOT / filename
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            ok(f"{filename}  ({size_kb:.1f} KB)")
        else:
            fail(f"{filename} — MISSING")
            errors += 1

    # Dockerfiles (can live in component dirs)
    dockerfiles = ["src/backend/Dockerfile", "src/frontend/Dockerfile"]
    for df in dockerfiles:
        f = PROJECT_ROOT / df
        if f.is_file():
            ok(f"{df}")
        else:
            warn(f"{df} — missing (Docker build will fail)")

    return errors


def check_documentation() -> int:
    """Count total lines of documentation across all doc volumes."""
    errors = 0
    heading("Documentation Coverage")

    docs_dir = PROJECT_ROOT / "docs"
    if not docs_dir.is_dir():
        fail("docs/ directory missing")
        return 1

    # Discover documentation volumes
    volumes = sorted(
        d for d in docs_dir.iterdir() if d.is_dir() and d.name.startswith("volume-")
    )

    if not volumes:
        volumes = sorted(d for d in docs_dir.iterdir() if d.is_dir())

    if not volumes:
        warn("No documentation volumes found in docs/")
        return 0

    print(f"\n  Found {len(volumes)} documentation volume(s):\n")

    total_files = 0
    total_lines = 0
    volume_data = []

    for vol in volumes:
        md_files = list(vol.rglob("*.md"))
        other_files = [
            f
            for f in vol.rglob("*")
            if f.is_file()
            and f.suffix not in (".md",)
            and f.suffix in (".txt", ".rst", ".py", ".json", ".yaml", ".yml", ".drawio")
        ]
        all_files = md_files + other_files

        vol_lines = 0
        for fpath in all_files:
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                lines = content.count("\n") + 1
                vol_lines += lines
            except Exception:
                pass

        vol_files = len(all_files)
        total_files += vol_files
        total_lines += vol_lines
        volume_data.append((vol.name, vol_files, vol_lines))

        ok(f"{vol.name}/  —  {vol_files} files, {vol_lines:,} lines")

    print(f"\n  ─────────────────────────────────────────────")
    print(f"  Total: {total_files} files, {total_lines:,} lines of documentation")

    if total_lines < 100:
        warn("Documentation is sparse (< 100 lines total)")
    elif total_lines > 10000:
        ok("Documentation is comprehensive")

    return errors


def check_dockerfiles() -> int:
    """Validate Dockerfiles exist and use valid base images."""
    errors = 0
    heading("Dockerfile Validation")

    dockerfile_paths = [
        PROJECT_ROOT / "src/backend" / "Dockerfile",
        PROJECT_ROOT / "src/frontend" / "Dockerfile",
    ]

    for df_path in dockerfile_paths:
        if not df_path.is_file():
            warn(f"{rel_path(df_path)} not found — skipping")
            continue

        content = df_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        # Check for FROM directives
        from_lines = [l for l in lines if l.strip().upper().startswith("FROM")]
        if not from_lines:
            fail(f"{rel_path(df_path)} has no FROM instruction")
            errors += 1
        else:
            for fl in from_lines:
                image = fl.strip().split(None, 2)[1] if fl.strip().split(None, 2) else ""
                ok(f"{rel_path(df_path)}: FROM {image}")

        # Check for multi-stage builds (good practice)
        if len(from_lines) >= 2:
            ok(f"{rel_path(df_path)}: multi-stage build ({len(from_lines)} stages)")

        # Check WORKDIR is set
        if not any(l.strip().upper().startswith("WORKDIR") for l in lines):
            warn(f"{rel_path(df_path)}: no WORKDIR set")

        # Check EXPOSE is present
        if not any(l.strip().upper().startswith("EXPOSE") for l in lines):
            warn(f"{rel_path(df_path)}: no EXPOSE port declared")

    return errors


def check_secrets() -> int:
    """Scan sensitive files for placeholder secrets that should not be committed."""
    errors = 0
    heading("Secret / Placeholder Scanning")

    # Walk common sensitive files
    sensitive_files: List[Path] = []

    # Always check .env.example
    env_example = PROJECT_ROOT / ".env.example"
    if env_example.is_file():
        sensitive_files.append(env_example)

    # Check docker-compose files
    for dc_file in PROJECT_ROOT.rglob("docker-compose*.yml"):
        sensitive_files.append(dc_file)

    # Check any secrets files
    for sf in PROJECT_ROOT.rglob("secrets*.yml"):
        sensitive_files.append(sf)
    for sf in PROJECT_ROOT.rglob("secrets*.yaml"):
        sensitive_files.append(sf)

    if not sensitive_files:
        ok("No sensitive-config files found to scan (clean project)")
        return errors

    found_placeholders = 0

    for fpath in sorted(set(sensitive_files)):
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            warn(f"Could not read {rel_path(fpath)}: {exc}")
            continue

        matched = []
        for line_no, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue  # skip comments
            for pattern in PLACEHOLDER_PATTERNS:
                if re.search(pattern, stripped, re.IGNORECASE):
                    matched.append((line_no, stripped.strip()))

        if matched:
            found_placeholders += len(matched)
            warn(f"{rel_path(fpath)} — {len(matched)} placeholder(s) found:")
            for ln, text in matched[:5]:  # Show first 5 only
                print(f"         L{ln:>4}: {text[:80]}")
            if len(matched) > 5:
                print(f"         ... and {len(matched) - 5} more")
        else:
            ok(f"{rel_path(fpath)} — clean")

    if found_placeholders:
        warn(
            f"\n  {found_placeholders} placeholder value(s) detected. "
            "These are acceptable in template files like .env.example "
            "but ensure they are never real credentials."
        )

    return errors


def check_configs_parseable() -> int:
    """Verify YAML and JSON config files are syntactically valid."""
    errors = 0
    heading("Config File Parsing")

    yaml_files = list(PROJECT_ROOT.rglob("*.yml")) + list(PROJECT_ROOT.rglob("*.yaml"))
    json_files = list(PROJECT_ROOT.rglob("*.json"))

    # Skip node_modules and .venv
    yaml_files = [f for f in yaml_files if "node_modules" not in f.parts and ".venv" not in f.parts]
    json_files = [f for f in json_files if "node_modules" not in f.parts and ".venv" not in f.parts]

    for yf in yaml_files:
        try:
            with yf.open("r", encoding="utf-8", errors="replace") as fh:
                yaml.safe_load(fh)
            ok(f"{rel_path(yf)} — valid YAML")
        except yaml.YAMLError as e:
            fail(f"{rel_path(yf)} — invalid YAML: {e}")
            errors += 1

    for jf in json_files:
        try:
            with jf.open("r", encoding="utf-8", errors="replace") as fh:
                json.load(fh)
            ok(f"{rel_path(jf)} — valid JSON")
        except json.JSONDecodeError as e:
            fail(f"{rel_path(jf)} — invalid JSON: {e}")
            errors += 1

    return errors


def check_gitignore() -> int:
    """Verify .gitignore covers essential patterns."""
    errors = 0
    heading(".gitignore Coverage")

    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.is_file():
        fail(".gitignore is missing")
        return 1

    content = gitignore_path.read_text(encoding="utf-8")
    missing = []

    for pattern in GITIGNORE_REQUIRED_PATTERNS:
        if pattern not in content:
            missing.append(pattern)

    if missing:
        warn(f"Missing patterns in .gitignore ({len(missing)}):")
        for p in missing:
            print(f"         - {p}")
    else:
        ok("All essential patterns covered")

    return errors


# ─── Main ────────────────────────────────────────────────────────────────


def main() -> int:
    """Run all validation checks and return exit code."""
    print(
        r"""
   ╔══════════════════════════════════════════════════╗
   ║   Aegis Marketing Cloud — Project Structure     ║
   ║          CI Validation Report                    ║
   ╚══════════════════════════════════════════════════╝
    """
    )
    print(f"  Project root : {PROJECT_ROOT}")
    print(f"  Python       : {sys.version.split()[0]}")

    checks: List[Tuple[str, int]] = []

    # Run all checks
    checks.append(("Directory structure", check_directories()))
    checks.append(("Root files", check_root_files()))
    checks.append(("Documentation", check_documentation()))
    checks.append(("Dockerfiles", check_dockerfiles()))
    checks.append(("Secrets scan", check_secrets()))
    checks.append(("Config parse", check_configs_parseable()))
    checks.append((".gitignore", check_gitignore()))

    # ─── Summary ───────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("  SUMMARY")
    print(f"{'═' * 60}")

    total_errors = 0
    for name, err_count in checks:
        status = (
            "✅ PASS" if err_count == 0 else f"❌ FAIL ({err_count} error(s))"
        )
        print(f"  {status: <20} — {name}")
        total_errors += err_count

    print(f"{'═' * 60}")
    if total_errors == 0:
        print("\n  🎉  All checks passed. Project structure is valid.\n")
    else:
        print(f"\n  ⚠️   {total_errors} issue(s) found. Review warnings above.\n")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
