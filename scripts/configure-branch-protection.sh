#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required" >&2
  exit 1
fi

REPO="${GITHUB_REPOSITORY:-}"
if [[ -z "$REPO" ]]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

required_contexts='["Promotion Gate / verify-promotion","Manifest Promotion / promote"]'

for branch in testing staging production; do
  echo "Configuring branch protection for $branch"
  gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    "/repos/${REPO}/branches/${branch}/protection" \
    -f required_status_checks.strict=true \
    -F required_status_checks.contexts[]="Promotion Gate / verify-promotion" \
    -F required_status_checks.contexts[]="Manifest Promotion / promote" \
    -f enforce_admins=true \
    -f required_pull_request_reviews.dismiss_stale_reviews=true \
    -f required_pull_request_reviews.required_approving_review_count=1 \
    -f restrictions= \
    -f allow_force_pushes=false \
    -f allow_deletions=false \
    -f block_creations=false \
    -f required_conversation_resolution=true

  gh api \
    --method POST \
    -H "Accept: application/vnd.github+json" \
    "/repos/${REPO}/branches/${branch}/protection/required_signatures" >/dev/null

done

echo "Branch protections and required signatures are configured for testing/staging/production."
