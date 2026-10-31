#!/usr/bin/env python3
"""Structural check for this skill: frontmatter, links, JSON, script syntax.

    python check_skill.py [skill_dir]
"""
from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    errors: list[str] = []
    skill = root / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        errors.append("SKILL.md is missing YAML frontmatter")
    else:
        fm = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", m.group(1), re.M))
        if fm.get("name") != root.name:
            errors.append(f"name should match the directory name: {fm.get('name')!r} vs {root.name!r}")
        if not re.fullmatch(r"[a-z0-9-]{1,64}", fm.get("name", "")):
            errors.append("name may only use lowercase letters, digits, and hyphens")
        desc = fm.get("description", "")
        if not desc:
            errors.append("missing description")
        elif len(desc) > 1024:
            errors.append(f"description too long: {len(desc)} > 1024")
        extra = set(fm) - {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
        if extra:
            errors.append(f"frontmatter has unknown fields: {sorted(extra)}")
    lines = text.count("\n")
    if lines > 500:
        errors.append(f"SKILL.md exceeds 500 lines: {lines}")

    for md in root.rglob("*.md"):
        for target in LINK_RE.findall(md.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+:", target) or target.startswith("{"):
                continue
            if not (md.parent / target).exists():
                errors.append(f"{md.relative_to(root)} broken link: {target}")

    for js in root.rglob("*.json"):
        try:
            json.loads(js.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{js.relative_to(root)} is not valid JSON: {e}")

    for py in (root / "scripts").glob("*.py"):
        try:
            py_compile.compile(str(py), doraise=True, cfile=None)
        except py_compile.PyCompileError as e:
            errors.append(f"{py.name} failed to compile: {e.msg}")

    for e in errors:
        print(f"FAIL  {e}")
    print("structure check passed" if not errors else f"\n{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
