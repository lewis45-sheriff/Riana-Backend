#!/usr/bin/env bash
# Deploy an immutable, checksum-verified artifact after CI and environment approval.
set -euo pipefail
mode=${1:?environment required}
sha=${2:?revision required}
[[ "$mode" == staging || "$mode" == production ]] || exit 2
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ "$(cat /etc/riana/environment)" == "$mode" ]] || { echo 'Wrong target server role' >&2; exit 2; }
component=backend
incoming="/tmp/riana-$component-$sha"
cd "$incoming"
sha256sum -c release.tgz.sha256
root="$HOME/apps/releases/$component-$mode"
release="$root/$sha"
envfile="$HOME/apps/environments/$mode-$component.env"
[[ -f "$envfile" ]] || { echo "Missing environment configuration: $envfile" >&2; exit 2; }
# Keep enough headroom to avoid filling the live server during extraction/install.
free_kb=$(df -Pk "$HOME" | awk 'NR==2 {print $4}')
[[ "$free_kb" -ge 204800 ]] || { echo 'Less than 200 MiB free; expand disk before deployment' >&2; exit 2; }
mkdir -p "$release"
# Artifacts are generated only from the checked-out revision by the gated build job.
tar -xzf release.tgz -C "$release"
previous=$(readlink -f "$root/current" || true)
service="riana-$component"
[[ "$mode" == production ]] || service="$service-staging"
port=8000
if [[ "$component" == backend ]]; then
  cd "$release"
  python3 -m venv .venv
  .venv/bin/pip install --no-cache-dir -q -r requirements.release.txt
  export RIANA_ENV_FILE="$envfile"
  if [[ "$mode" == staging ]]; then
    .venv/bin/python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
if settings.DATABASES['default']['NAME'] != 'riana_staging':
    raise SystemExit('Staging must use the riana_staging database')
if settings.SMTP_HOST or settings.AFRICASTALKING_API_KEY or settings.SMSGATE_PASSWORD:
    raise SystemExit('Staging outbound integrations must be disabled')
PY
  fi
  .venv/bin/python manage.py check
  # Migrations run on the target environment, before switching the active release.
  .venv/bin/python manage.py migrate --noinput
  if [[ "$mode" == staging ]]; then
    .venv/bin/python manage.py seed_user
    .venv/bin/python manage.py seed
  fi
fi
unit="/etc/systemd/system/$service.service"
backup="$root/unit-before-$sha.service"
if [[ -f "$unit" ]]; then sudo cp -p "$unit" "$backup"; fi
ln -sfn "$release" "$root/next-current"
mv -Tf "$root/next-current" "$root/current"
user=$(id -un)
if [[ "$component" == backend ]]; then
  command="$root/current/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:$port --workers 2 --timeout 90"
else
  command="$(command -v node) $root/current/server.js"
fi
sudo tee "$unit" >/dev/null <<UNIT
[Unit]
Description=Riana $component ($mode)
After=network.target
[Service]
User=$user
WorkingDirectory=$root/current
EnvironmentFile=$envfile
Environment=RIANA_ENV_FILE=$envfile
ExecStart=$command
Restart=on-failure
RestartSec=3
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable "$service" >/dev/null
sudo systemctl restart "$service"
path=/
[[ "$component" == backend ]] && path=/health
if ! curl --fail --silent --show-error --retry 12 --retry-connrefused --retry-delay 2 \
    --max-time 10 "http://127.0.0.1:$port$path" >/dev/null; then
  echo 'Smoke test failed; restoring prior application release (database is not rolled back)' >&2
  if [[ -n "$previous" && -d "$previous" && "$previous" != "$release" ]]; then
    ln -sfn "$previous" "$root/next-current"
    mv -Tf "$root/next-current" "$root/current"
  fi
  if [[ -f "$backup" ]]; then sudo cp -p "$backup" "$unit"; fi
  sudo systemctl daemon-reload
  sudo systemctl restart "$service" || true
  exit 1
fi
printf '%s %s deployed revision %s; smoke test passed\n' "$component" "$mode" "$sha"
