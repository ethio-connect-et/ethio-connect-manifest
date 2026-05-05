#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="${1:-ethio-connect-et/ethio-connect-manifest}"
RUN_STATUS="${2:-completed}"

if [[ "$REPO_SLUG" != */* ]]; then
  echo "❌ Invalid repository '$REPO_SLUG'. Expected format: owner/repo"
  exit 1
fi

OWNER="${REPO_SLUG%%/*}"
REPO="${REPO_SLUG##*/}"

# Ensure gh is authenticated
if ! gh auth status >/dev/null 2>&1; then
  echo "❌ GitHub CLI not authenticated. Run: gh auth login"
  exit 1
fi

echo "🔍 Fetching ALL completed workflow runs for $OWNER/$REPO"

# Fetch all completed workflow run IDs (pagination handled)
if ! RUN_IDS_RAW="$(
  gh api \
    "repos/$OWNER/$REPO/actions/runs?status=$RUN_STATUS&per_page=100" \
    --paginate \
    --jq '.workflow_runs[].id'
)"; then
  echo "❌ Failed to fetch workflow runs for $OWNER/$REPO"
  echo "   Verify repository name/access and GitHub CLI permissions."
  exit 1
fi

mapfile -t RUN_IDS < <(printf '%s\n' "$RUN_IDS_RAW" | awk 'NF')

TOTAL=${#RUN_IDS[@]}

if (( TOTAL == 0 )); then
  echo "✅ No completed workflow runs found"
  exit 0
fi

echo "🧹 Found $TOTAL completed workflow runs. Deleting..."

DELETED=0

for RUN_ID in "${RUN_IDS[@]}"; do
  if [[ ! "$RUN_ID" =~ ^[0-9]+$ ]]; then
    echo "⚠️  Skipping invalid workflow run ID value: $RUN_ID"
    continue
  fi

  echo "🗑️  Deleting workflow run ID: $RUN_ID"
  gh api \
    --method DELETE \
    "repos/$OWNER/$REPO/actions/runs/$RUN_ID"
  ((DELETED += 1))
done

echo "✅ Deleted $DELETED completed workflow runs successfully"
