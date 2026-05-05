#!/usr/bin/env python3
"""Apply an immutable image digest promotion to the matching GitOps patch file."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

APP_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
ENVS = {"testing", "staging", "production"}
REGISTRY = "ghcr.io/ethio-connect-et"
IMAGE_RE = re.compile(r"(?P<prefix>^\s*image:\s*)(?P<quote>[\"']?)(?P<image>ghcr\.io/ethio-connect-et/(?P<app>[a-z0-9][a-z0-9._-]*)(?:@sha256:[a-f0-9]{64}|:[^\s\"']+))(?P=quote)\s*$", re.MULTILINE)
DEPLOYMENT_RE = re.compile(r"^\s*name:\s*(?P<name>[a-z0-9][a-z0-9.-]*)\s*$", re.MULTILINE)


def fail(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


def validate_inputs(environment: str, app: str, digest: str) -> None:
    if environment not in ENVS:
        fail(f"environment must be one of {', '.join(sorted(ENVS))}: {environment}")
    if not APP_RE.match(app):
        fail(f"app must match {APP_RE.pattern}: {app}")
    if not DIGEST_RE.match(digest):
        fail(f"digest must match {DIGEST_RE.pattern}: {digest}")


def patch_candidates(environment: str, app: str) -> list[Path]:
    overlay = Path("overlays") / environment
    if not overlay.is_dir():
        fail(f"overlay directory not found: {overlay}")

    matches: list[Path] = []
    for patch in sorted(overlay.glob("*/patch.yaml")):
        text = patch.read_text(encoding="utf-8")
        image_apps = {match.group("app") for match in IMAGE_RE.finditer(text)}
        named_resources = {match.group("name") for match in DEPLOYMENT_RE.finditer(text)}
        if app in image_apps or app in named_resources:
            matches.append(patch)
    return matches


def replace_image(patch: Path, app: str, digest: str) -> int:
    new_image = f"{REGISTRY}/{app}@{digest}"
    updated_lines: list[str] = []
    replacements = 0

    for line in patch.read_text(encoding="utf-8").splitlines(keepends=True):
        newline = "\n" if line.endswith("\n") else ""
        body = line[:-1] if newline else line
        match = IMAGE_RE.match(body)
        if match and match.group("app") == app:
            quote = match.group("quote")
            updated_lines.append(f"{match.group('prefix')}{quote}{new_image}{quote}{newline}")
            replacements += 1
        else:
            updated_lines.append(line)

    if replacements == 0:
        fail(f"no image reference for app {app} found in {patch}")

    patch.write_text("".join(updated_lines), encoding="utf-8")
    return replacements


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True)
    parser.add_argument("--app", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--attestation", default="artifacts/promotion-attestation.json")
    args = parser.parse_args()

    validate_inputs(args.environment, args.app, args.digest)
    matches = patch_candidates(args.environment, args.app)
    if not matches:
        fail(
            f"unable to map app {args.app} to a patch file under overlays/{args.environment}; "
            "the source repo dispatch app name must match a Deployment/image name"
        )
    if len(matches) > 1:
        fail(f"app {args.app} maps to multiple patch files: {', '.join(str(p) for p in matches)}")

    patch = matches[0]
    replacements = replace_image(patch, args.app, args.digest)

    attestation_path = Path(args.attestation)
    attestation_path.parent.mkdir(parents=True, exist_ok=True)
    attestation = {
        "app": args.app,
        "environment": args.environment,
        "digest": args.digest,
        "image": f"{REGISTRY}/{args.app}@{args.digest}",
        "patch_file": str(patch),
        "replacements": replacements,
        "promoted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    attestation_path.write_text(json.dumps(attestation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(attestation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
