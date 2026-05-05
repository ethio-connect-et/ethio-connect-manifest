# GitOps Promotion Contract

## Repositories and handoff

- Source/application repository: `ethio-connect-et/ethio-connect`.
- GitOps/manifest repository: `ethio-connect-et/ethio-connect-manifest`.
- Deployment model: GitHub Actions updates Git only; Argo CD and Rancher perform pull-based deployment from the environment branches.

The current source repository workflow publishes GHCR images on `testing`, `staging`, and `main`, resolves immutable image digests, and dispatches `promote-image` events to this repository. The branch mapping is:

| Source branch | Manifest branch | Cluster environment |
|---|---|---|
| `testing` | `testing` | Testing |
| `staging` | `staging` | Staging |
| `main` | `production` | Production |

## Accepted `repository_dispatch` payload schema

Event type: `promote-image`.

Minimum required `client_payload` keys aligned with the current source repo `scripts/manifest-dispatch.sh` implementation:

- `app` (string): Docker target/deployment image name, for example `vendor-portal-api`.
- `env` (string): one of `testing`, `staging`, `production`.
- `digest` (string): must match `^sha256:[a-f0-9]{64}$`.

Optional forward-compatible metadata accepted by this repository:

- `source_repo`: must equal `ethio-connect-et/ethio-connect` when supplied.
- `source_ref`: must match the branch mapping (`testing`, `staging`, or `main`) when supplied.
- `source_commit`: source commit SHA.
- `release_id`, `release_created_at`, `signed_metadata`, `attestation_bundle`: release/audit metadata for future source workflow hardening.

## Promotion workflow

1. `Receive Source Promotion` validates the repository dispatch payload.
2. The workflow checks out the target environment branch.
3. `.github/scripts/promote_manifest.py` maps `app` to the single overlay patch containing that deployment/image.
4. The workflow rewrites only that app image to `ghcr.io/ethio-connect-et/${APP}@${DIGEST}`.
5. The workflow verifies the diff touches exactly one target overlay patch.
6. A promotion attestation artifact is uploaded with explicit retention.
7. A bot PR is opened against `testing`, `staging`, or `production`.
8. `Manifest Validation` renders Helm/Kustomize manifests, uploads rendered artifacts, validates schemas, enforces image policy, and runs OPA policies when present.
9. `Promotion Gate` publishes rollout readiness commit statuses; production requires the `production-change-control` GitHub environment gate.
10. After checks and merge, Argo CD pulls the branch update into the Rancher-managed bare-metal Ubuntu Kubernetes cluster.

## Canonical image reference format

All runtime images must use immutable digest references:

```text
ghcr.io/ethio-connect-et/${APP}@sha256:<64hex>
```

Mutable tags are forbidden in rendered manifests and deploy overlays.

## Rollback contract

Rollbacks are GitOps PRs too. `Rollback Promotion` requires:

- app name,
- environment,
- previous-good digest,
- change ticket/reference.

The workflow verifies the previous-good digest is present in the target patch file history before opening a rollback PR.

## Architecture diagrams

- CI/CD and GitOps flow: [`docs/resources/ethio-connect-gitops-cicd.mermaid`](resources/ethio-connect-gitops-cicd.mermaid)
- Bare-metal platform architecture: [`docs/resources/ethio-connect-baremetal-architecture.mermaid`](resources/ethio-connect-baremetal-architecture.mermaid)
