#!/usr/bin/env bash
# Install the launchd job that keeps the iNaturalist context line: scripts/cache_inaturalist.py, daily.
#   bash scripts/install_inaturalist_job.sh            -> installs and loads the job
#   bash scripts/install_inaturalist_job.sh --remove   -> unloads and removes it
#
# The Worker never asks iNaturalist. This Mac does, once a day: it reads the creeks' Locations from
# our own public API, asks iNaturalist's public API about the plants on the region's invasive list
# near them (at most one request a second, a user agent that names this project), and stores a
# short summary per creek in D1 (worker/src/inaturalist.ts). launchd runs it as Alex, with the same
# wrangler login the backup uses, so it needs no secret.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.secondlook.inaturalist"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/second-look-backups/logs"
UV="$(command -v uv)"

if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "inaturalist-job: removed"
  exit 0
fi

mkdir -p "$(dirname "$PLIST")" "$LOG_DIR"
cat > "$PLIST" <<PLIST_END
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$UV</string>
    <string>run</string>
    <string>python</string>
    <string>$ROOT/scripts/cache_inaturalist.py</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>45</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG_DIR/inaturalist.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/inaturalist.err</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
</dict>
</plist>
PLIST_END

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "inaturalist-job: installed $PLIST"
echo "inaturalist-job: runs daily at 07:45 local; log in $LOG_DIR/inaturalist.log"
launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state|path =" | head -3 || true
