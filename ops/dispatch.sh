#!/usr/bin/env bash
set -euo pipefail
mode=${1:?environment required}
sha=${2:?revision required}
[[ "$mode" == staging || "$mode" == production ]] || exit 2
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
for name in DEPLOY_HOST DEPLOY_USER DEPLOY_KEY DEPLOY_HOST_KEYS; do
  [[ -n "${!name:-}" ]] || { echo "Missing deployment configuration: $name" >&2; exit 2; }
done
[[ "$DEPLOY_HOST" =~ ^[a-zA-Z0-9.-]+$ ]] || exit 2
[[ "$DEPLOY_USER" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
sha256sum -c release.tgz.sha256
keydir=$(mktemp -d)
trap 'rm -f "$keydir/key" "$keydir/known_hosts"; rmdir "$keydir"' EXIT
printf '%s\n' "$DEPLOY_KEY" > "$keydir/key"
printf '%s\n' "$DEPLOY_HOST_KEYS" > "$keydir/known_hosts"
chmod 600 "$keydir/key" "$keydir/known_hosts"
sshargs=(-i "$keydir/key" -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$keydir/known_hosts")
target="$DEPLOY_USER@$DEPLOY_HOST"
incoming="/tmp/riana-backend-$sha"
ssh "${sshargs[@]}" "$target" "mkdir -p '$incoming'"
scp "${sshargs[@]}" release.tgz release.tgz.sha256 ops/deploy.sh "$target:$incoming/"
ssh "${sshargs[@]}" "$target" "bash '$incoming/deploy.sh' '$mode' '$sha'"
