#!/usr/bin/env bash
clear && set -euo pipefail

VERSION_FILE="./scripts/.ci_version"
TARGET_BRANCH="development"
REPO_HTTPS="https://github.com/ethio-connect-et/ethio-connect-manifest.git"

# Step 1: Ensure remote is accessible
if ! git ls-remote "$REPO_HTTPS" &>/dev/null; then
  echo "ERROR: Cannot access remote repository $REPO_HTTPS. Check network or credentials."
  exit 1
fi

# Step 2: Run format and lint with explicit error handling
pnpm exec actionlint -color

# Step 3: Read current version
CURRENT=$(cat "$VERSION_FILE")

# Step 4: Increment
NEXT=$((CURRENT + 1))
echo "$NEXT" > "$VERSION_FILE"

# Step 5: Stage changes
git add -A
git add "$VERSION_FILE"

# Step 6: Commit
git commit -q -m "CI-UPDATE-$NEXT"

# Step 7: Ensure remote uses HTTPS
git remote set-url origin "$REPO_HTTPS"

# Step 8: Create feature branch
BRANCH="feat/commit-$NEXT"
git checkout -b "$BRANCH"

# Step 9: Push branch
git push -u origin "$BRANCH"

# Step 10: Ensure target branch exists
if git ls-remote --exit-code origin "refs/heads/$TARGET_BRANCH" &>/dev/null; then
  git fetch origin "$TARGET_BRANCH"
else
  echo "ERROR: Remote branch '$TARGET_BRANCH' does not exist on origin."
  exit 1
fi

# Step 11: Create PR to target branch
DATE=$(date +"%b %d, %Y %H:%M:%S")
gh pr create \
  --base "$TARGET_BRANCH" \
  --head "$BRANCH" \
  --title "CI-UPDATE-$NEXT ($DATE)" \
  --body "Automated CI version increment to $NEXT on $DATE."

# Step 12: Return to target branch
git checkout "$TARGET_BRANCH"
git branch -D "$BRANCH"
