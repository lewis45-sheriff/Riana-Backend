# Gated CI/CD and environment setup

Each repository now has its own active `.github/workflows/deploy.yml`.

## Release flow

1. Every push and pull request to main runs lint and tests. Backend tests and
   migration checks use a PostgreSQL service; frontend tests use Vitest.
2. CI builds a Docker image, scans source dependencies/secrets and scans the
   built image with Trivy. HIGH/CRITICAL findings fail the job. Scans do not use
   continue-on-error or an exit-code of zero to suppress failures.
3. CI packages the exact checked-out revision and attaches a SHA-256 checksum.
   Backend packages source plus the resolved dependency versions. Frontend
   packages Next.js standalone output built with an empty NEXT_PUBLIC_API_URL,
   so the same release uses the origin of staging or production.
4. Main deploys the artifact to the staging environment. Target migrations and
   local health smoke tests must pass. Staging has an independent database and
   no outbound SMTP, AI, SMS provider keys or production customer data.
5. A policy job checks that production has a required-reviewer rule.
6. The production job waits for GitHub Environment approval, downloads the same
   staging-tested artifact, checks its checksum, migrates and smoke-tests it.
   A failed dependency job skips production. No job fetches the latest main to
   deploy different code from the tested SHA.

Docker images are build/scan gates. Deployment uses native systemd releases to
match the existing EC2 setup, rather than running those images on the hosts.
The code and release artifact are promoted unchanged; backend Python minor
versions must be compatible with the resolved dependencies.

## GitHub settings

Create `staging` and `production` environments in BOTH repositories.
Restrict deployment branches to `main`. On production configure a required
reviewer and disallow administrator bypass. A single-maintainer repository can
allow the author to manually approve their own run; independent review requires
another reviewer and enabling prevent-self-review.

Staging environment secrets (distinct names prevent falling back to production):

- STAGING_EC2_HOST
- STAGING_EC2_USER
- STAGING_EC2_SSH_KEY

Staging variables:

- STAGING_SSH_HOST_KEYS: a complete pinned known_hosts line, not a fingerprint.
- STAGING_URL: the staging app URL.

Production uses existing EC2_HOST, EC2_USER, EC2_SSH_KEY secrets and the variable
PRODUCTION_SSH_HOST_KEYS. Private keys go into Actions secrets only, never into
Git or build artifacts. SSH checks the pinned host key and refuses unknown hosts.

Protect main against bypassing CI as well: require a pull request and the quality
and build/scan checks before merging. Environment approval is a release control;
branch protection is a separate merge control. Do not approve a production run
until its staging version has been reviewed.

## Target server layout

- /etc/riana/environment contains exactly staging or production.
- ~/apps/environments/ENV-backend.env contains backend-only settings, mode 600.
- ~/apps/environments/ENV-frontend.env contains PORT=3000,
  HOSTNAME=127.0.0.1, NODE_ENV=production.
- ~/apps/releases/COMPONENT-ENV/SHA holds immutable release files.
- ~/apps/releases/COMPONENT-ENV/current points at the active release.
- Services: riana-backend-staging / riana-frontend-staging on staging;
  riana-backend / riana-frontend on production.
- Nginx proxies /api/ and /health to 127.0.0.1:8000 and the frontend to port 3000.

The deployment script refuses a host whose role marker does not match the job.
It refuses missing environment files and less than 200 MiB free disk. This is a
minimum preflight, not a guarantee that every future artifact fits: size the disk
for two application releases, virtual environments and temporary archives. Never
copy production integration credentials or customer data into staging.

Backend settings honor RIANA_ENV_FILE so management commands and systemd load the
same environment-specific settings outside the immutable release directory. On
the existing production host the production backend env file can be a symlink to
~/apps/backend/.env; this keeps credentials outside the artifacts.

## Migrations, smoke tests and rollback

Backend checks configuration and applies migrations before changing current.
Database changes must be backward-compatible with the previous application.
Application smoke-test failure restores the prior unit/current link when available.
This does NOT reverse database migrations or undo external side effects. Back up
the production database and review migration reversibility before approval.

Keep the last known good release until the new one is verified. Release folders
are not automatically deleted; monitor disk usage and remove only reviewed inactive
releases. Backend and frontend repositories have independent release runs, so use
backward-compatible API changes when promoting them separately.

First-time staging frontend checks require the backend to have been deployed for
a complete end-to-end review. Local service health is checked by the deployment;
verify public HTTPS and a login/survey flow separately before production approval.

## Operational notes

Do not run the legacy ~/apps/deploy_backend.sh or deploy_frontend.sh scripts as part
of CI. They pull main and bypass artifact promotion. They remain only as historical
files on the original host and are not referenced by the active workflows.

The workspace root CI template is outside the two repositories and is not the
active pipeline. Use each repository's workflow and this document for hand-in.
