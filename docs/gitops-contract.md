# GitOps Promotion Contract

## Accepted `repository_dispatch` payload schema

Event type: `promote-image`

Required `client_payload` keys:

- `app` (string): must match an app directory under `overlays/<env>/<app>/patch.yaml`.
- `env` (string): one of `testing`, `staging`, `production`.
- `digest` (string): must match `^sha256:[a-f0-9]{64}$`.

Optional for manual dry-run via `workflow_dispatch`:

- `dry_run` (boolean): when `true`, payload validation and file mapping are executed without PR creation.

## Branch / environment mapping

- `testing` payloads target the `testing` base branch.
- `staging` payloads target the `staging` base branch.
- `production` payloads target the `production` base branch.

Promotion updates are restricted to exactly one file:

- `overlays/${ENVIRONMENT}/${APP}/patch.yaml`

Any missing file, mismatch, or additional modified path fails promotion.

## Canonical image reference format

Promotion rewrites image references to the canonical digest-pinned form:

- `ghcr.io/ethio-connect-et/${APP}@${DIGEST}`

No mutable tags are used by the promotion workflow.

## Failure handling and retry semantics

Validation failures are hard-stop failures and do not create PRs:

- malformed payload (`app`, `env`, `digest` invalid),
- unsupported app for selected environment,
- missing or mismatched patch target,
- diff integrity failure (changed files not exactly the expected patch file).

Retry behavior:

1. Fix upstream payload generation or manifest layout issue.
2. Re-dispatch the same event with corrected payload values.
3. For manual testing, run `workflow_dispatch` with `dry_run=true` before sending live `repository_dispatch` events.

Safety net validation:

- `Manifest Validation / contract-validation` replays sample payload semantics for `testing`, `staging`, and `production` against all discovered apps to detect schema/mapping drift early.
