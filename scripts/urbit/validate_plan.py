#!/usr/bin/env python3
"""Validate planning metadata only. Does not test Urbit or production security."""
from __future__ import annotations
import json
from pathlib import Path
import sys

def validate(root: Path) -> int:
    try:
        data = json.loads((root / "specs/urbit/backlog.json").read_text())
        items = data["issues"]
        ids = [item["id"] for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate backlog IDs")
        known = set(ids)
        edges = {}
        for item in items:
            for field in ("id", "title", "phase", "owner_role", "status", "depends_on", "acceptance"):
                if field not in item:
                    raise ValueError(f"Missing {field}: {item}")
            if item["status"] != "planned":
                raise ValueError(f"Unsubstantiated completion status: {item['id']}")
            if not item["acceptance"]:
                raise ValueError(f"Missing acceptance criteria: {item['id']}")
            missing = set(item["depends_on"]) - known
            if missing:
                raise ValueError(f"Unknown dependencies: {missing}")
            edges[item["id"]] = item["depends_on"]
        active, finished = set(), set()
        def visit(node):
            if node in active:
                raise ValueError(f"Dependency cycle at {node}")
            if node in finished:
                return
            active.add(node)
            for dep in edges[node]:
                visit(dep)
            active.remove(node)
            finished.add(node)
        for node in edges:
            visit(node)
        for name in ("MASTER_BUILD_DIRECTIVE", "DEPLOYMENT", "ROADMAP", "AGENT_HANDOFF", "SOURCES"):
            if not (root / f"docs/urbit/{name}.md").is_file():
                raise ValueError(f"Missing document: {name}")
        lock = json.loads((root / "specs/urbit/toolchain.lock.example.json").read_text())
        if lock["status"] != "unresolved_example_not_executable":
            raise ValueError("Example lock must not imply a resolved executable toolchain")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL (planning metadata): {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {len(items)} planning tasks, acyclic dependencies, required documents present.")
    print("NOT TESTED HERE: Hoon compilation, live Urbit, GitHub publishing, security, performance, cloud deployment.")
    return 0

if __name__ == "__main__":
    raise SystemExit(validate(Path(__file__).resolve().parents[2]))
