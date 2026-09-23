#!/usr/bin/env bash
# Install the launchd job that keeps /two's lab record: scripts/cache_their_records.py, daily.
#   bash scripts/install_cache_job.sh            -> installs and loads the job
#   bash scripts/install_cache_job.sh --remove   -> unloads and removes it
#
# Their sandbox does not answer the Cloudflare Worker, so this Mac fetches the one record /two
# shows and stores it in D1 (worker/src/two.ts). launchd runs it as Alex, with the same wrangler
# login the backup uses, so it needs no secret. One read-only GET to their sandbox per run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.secondlook.theirs"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/second-look-backups/logs"
UV="$(command -v uv)"

if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "theirs-job: removed"
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
    <string>$ROOT/scripts/cache_their_records.py</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG_DIR/theirs.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/theirs.err</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
</dict>
</plist>
PLIST_END

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "theirs-job: installed $PLIST"
echo "theirs-job: runs daily at 07:30 local; log in $LOG_DIR/theirs.log"
launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state|path =" | head -3 || true
