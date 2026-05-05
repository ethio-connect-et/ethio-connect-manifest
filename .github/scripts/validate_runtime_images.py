#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from pathlib import Path

CANONICAL_RE = re.compile(r"^ghcr\.io/ethio-connect-et/[a-z0-9][a-z0-9._-]*@sha256:[a-f0-9]{64}$")
TAG_RE = re.compile(r":(?!//)[^\s@]+$")
IMAGE_LINE_RE = re.compile(r"^\s*image:\s*\"?([^\"\s]+)\"?\s*$")

ENV_FILES = {
    "testing": Path("/tmp/testing.yaml"),
    "staging": Path("/tmp/staging.yaml"),
    "production": Path("/tmp/production.yaml"),
}


def check_rendered_manifests() -> list[str]:
    errors: list[str] = []
    for env, path in ENV_FILES.items():
        if not path.exists():
            errors.append(
                f"missing rendered manifest for {env}: {path}. "
                f"Run 'kustomize build --enable-helm overlays/{env} > {path}' to generate it."
            )
            continue
        for idx, line in enumerate(path.read_text().splitlines(), 1):
            m = IMAGE_LINE_RE.match(line)
            if not m:
                continue
            image = m.group(1)
            if not CANONICAL_RE.match(image):
                errors.append(
                    f"{path}:{idx} [{env}] non-canonical image reference: {image} "
                    "(expected ghcr.io/ethio-connect-et/<app>@sha256:<64hex>)"
                )
            if TAG_RE.search(image):
                errors.append(f"{path}:{idx} [{env}] mutable tag-style image reference is forbidden: {image}")
    return errors


def changed_overlay_paths() -> list[str]:
    event = os.getenv("GITHUB_EVENT_NAME", "")
    if event != "pull_request":
        return []

    base = os.getenv("GITHUB_BASE_REF")
    if not base:
        return []

    subprocess.run(["git", "fetch", "--no-tags", "--depth=1", "origin", base], check=True)
    diff = subprocess.check_output(["git", "diff", "--name-only", f"origin/{base}...HEAD"], text=True)

    targets: list[str] = []
    for rel in diff.splitlines():
        if rel.startswith("overlays/testing/") or rel.startswith("overlays/staging/") or rel.startswith("overlays/production/"):
            targets.append(rel)
    return targets


def check_changed_overlay_files(paths: list[str]) -> list[str]:
    errors: list[str] = []
    image_ref_re = re.compile(r"ghcr\.io/ethio-connect-et/[a-zA-Z0-9._/-]+(?:@sha256:[a-f0-9]{64}|:[^\s\"']+)")

    for rel in paths:
        p = Path(rel)
        if not p.exists() or p.is_dir():
            continue
        for idx, line in enumerate(p.read_text().splitlines(), 1):
            for match in image_ref_re.finditer(line):
                image = match.group(0)
                if ":" in image and "@sha256:" not in image:
                    errors.append(f"{rel}:{idx} mutable tag reference detected in deploy overlay: {image}")
                if "@sha256:" in image and not CANONICAL_RE.match(image):
                    errors.append(
                        f"{rel}:{idx} non-canonical digest ref in deploy overlay: {image} "
                        "(must be ghcr.io/ethio-connect-et/<app>@sha256:<64hex>)"
                    )
    return errors


def main() -> int:
    errors = []
    errors.extend(check_rendered_manifests())
    overlay_changes = changed_overlay_paths()
    if overlay_changes:
        errors.extend(check_changed_overlay_files(overlay_changes))

    if errors:
        print("Runtime image policy violations:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    print("Runtime image policy checks passed for testing/staging/production.")
    if overlay_changes:
        print("Checked changed overlay files:")
        for path in overlay_changes:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
