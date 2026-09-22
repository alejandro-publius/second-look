#!/usr/bin/env bash
# Install the launchd job that backs the study database up daily at 21:00 and again at wake.
#   bash scripts/install_backup_job.sh            -> installs and loads the job
#   bash scripts/install_backup_job.sh --remove   -> unloads and removes it
#
# launchd runs it as Alex, so it uses the same wrangler login and needs no secret. A missed run,
# because the Mac was asleep at 21:00, is caught by the wake trigger (Update 11D item 4).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.secondlook.backup"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/second-look-backups/logs"

if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "backup-job: removed"
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
    <string>/bin/bash</string>
    <string>$ROOT/scripts/backup_d1.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG_DIR/backup.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/backup.err</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
</dict>
</plist>
PLIST_END

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "backup-job: installed $PLIST"
echo "backup-job: runs daily at 21:00 local; a run missed while asleep is caught at wake"
launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state|path =" | head -3 || true
