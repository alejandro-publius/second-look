#!/usr/bin/env bash
# Install the launchd job that anchors the audit log once a day with OpenTimestamps (UPDATE_29
# section 3): scripts/anchor_audit_head.py stamps the log's last hash with ots stamp, then
# scripts/ots_status.py runs ots upgrade on every proof and writes results/ots.json.
#   bash scripts/install_anchor_job.sh            -> installs and loads the job
#   bash scripts/install_anchor_job.sh --remove   -> unloads and removes it
#
# Only hashes leave this Mac, sent to the public OpenTimestamps calendars. The job commits
# nothing: new and upgraded proofs wait in proofs/ of this checkout for the next commit.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.secondlook.anchor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/second-look-backups/logs"
UV="$(command -v uv)"

if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "anchor-job: removed"
  exit 0
fi

# The status runs even when there was nothing new to stamp, so pending proofs still upgrade.
# No ampersand: this string goes into XML. WorkingDirectory below is the checkout.
RUN="'$UV' run python scripts/anchor_audit_head.py; '$UV' run python scripts/ots_status.py"

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
    <string>-c</string>
    <string>$RUN</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG_DIR/anchor.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/anchor.err</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
</dict>
</plist>
PLIST_END

plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "anchor-job: installed $PLIST"
echo "anchor-job: daily at 06:00 local, ots stamp then ots upgrade; log in $LOG_DIR/anchor.log"
