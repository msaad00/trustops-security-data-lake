# Deploy

Three install surfaces — pick the one that fits your blast radius.

| Surface             | When to use                                                 | Command                                                                                        |
| ------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Python wheel**    | Local demos, single laptop, contributor onboarding          | `pip install trustops-security-data-lake && security-lakehouse serve --lake build/lakehouse`   |
| **Container image** | CI, Docker Compose, single-host servers                     | `docker run -p 8787:8787 -v $PWD/build/lakehouse:/lake ghcr.io/msaad00/trustops:latest`        |
| **Helm + EKS**      | Production self-hosted, customer-data-residency requirement | See [Helm chart](helm/trustops/) + [EKS reference IaC](eks-terraform/) below                   |
| **Snowflake POC**   | Governed evidence lake using customer-owned Snowflake views | Run [`snowflake/bootstrap_poc.sql`](snowflake/bootstrap_poc.sql), then connect the reader role |

## Container image

The repo ships a multi-stage `Dockerfile` at the root. Build locally:

```bash
make docker-build              # builds tag trustops:dev
docker run --rm -p 8787:8787 -v $PWD/build/lakehouse:/lake trustops:dev
```

Notes:

- The image bundles the Next.js workbench (built in stage 1) inside the Python wheel (stage 2) so the runtime image has no Node dependency.
- Runs as UID 1100 (non-root) with `readOnlyRootFilesystem` compatible defaults.
- Listens on `:8787`; `/api/healthz` is the liveness probe.

## Helm chart

Renders in any conformant Kubernetes ≥ 1.27:

```bash
helm install trustops ./deploy/helm/trustops \
  --namespace trustops --create-namespace \
  --set image.tag=0.1.0 \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=trustops.example.com
```

Key value groups:

- `image` — repository, tag, pull policy, pull secrets.
- `lake.persistence` — PVC backing for `gold/` + `silver/` + `bronze/` (use a CSI driver that supports `ReadWriteMany` only if you also run multiple replicas).
- `serviceAccount.annotations` — bind an IRSA role (EKS) or Workload Identity (GKE) here for read-only access to the customer evidence bucket.
- `scheduler` — opt-in CronJob that runs `security-lakehouse scheduler tick` to fire `trigger.cron` workflows. Disable with `scheduler.enabled=false` if you drive it from an external scheduler.
- `defaultTrustRole` — set to `auditor` for the Trust Center deployment so it serves the redacted projection by default.

`helm lint deploy/helm/trustops` and `helm template trustops deploy/helm/trustops` both run in CI.

## EKS reference IaC

`deploy/eks-terraform/` provisions a minimal but real EKS cluster:

- VPC with public + private subnets across 2 AZs
- EKS managed control plane + one managed node group
- OIDC provider for IRSA
- IAM role bound to the `trustops` ServiceAccount, with **read-only** access to your customer evidence S3 bucket
- Helm release of the chart with that IRSA annotation applied

```bash
cd deploy/eks-terraform
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars               # set evidence_bucket_name
terraform init
terraform plan
terraform apply
$(terraform output -raw kubeconfig_update_command)
kubectl -n trustops get pods
```

The IAM policy is intentionally tiny: `s3:ListBucket` + `s3:GetObject*` on the named evidence bucket. No write/delete actions, no other AWS resources. That's the customer-data-residency boundary: TrustOps reads where the data lives, and the principal it runs as can't move bytes anywhere else.

## Snowflake POC bootstrap

`deploy/snowflake/bootstrap_poc.sql` creates a minimal existing-lake proof:

- `TRUSTOPS_SECURITY_LAKE.EVIDENCE` for curated evidence views
- `TRUSTOPS_READ_WH` as an XSMALL auto-suspended read warehouse
- `TRUSTOPS_READER` with imported privileges on `SNOWFLAKE` plus USAGE/SELECT
- four secure views over `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY`

Run it from a Snowflake role allowed to create a database, warehouse, role, and
grants. The script does not create users, stages, integrations, external
network access, or credential material. After it returns counts for the four
views, connect TrustOps with the `snowflake-evidence-lake` connector and browser
SSO or OAuth.

## What's not in this PR

- ECR repo + image push pipeline (use `ghcr.io/msaad00/trustops` from a public release for now).
- Cross-account bucket policy examples (the IRSA role can already assume into another account if the bucket policy allows).
- GKE / AKS reference IaC — same chart works; pull-requests welcome.
