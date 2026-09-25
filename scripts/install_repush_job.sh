#!/usr/bin/env bash
# Install the launchd job that keeps retrying their sandbox, daily at 08:00 (UPDATE_30 section
# 6.1): scripts/sandbox_retry.py asks whether the sandbox's name resolves, and when it does puts
# our Library entry and the golden visit back by conditional create, refreshes /two's cache and
# writes a line to the status issue. It logs to ~/second-look-backups/logs/repush.log.
#   bash scripts/install_repush_job.sh            -> installs and loads the job
#   bash scripts/install_repush_job.sh --remove   -> unloads and removes it
# `make mac-jobs-install` installs this job with all the others (scripts/mac_jobs.py); a test
# keeps the two the same.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.secondlook.repush"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/second-look-backups/logs"
UV="$(command -v uv)"

if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "repush-job: removed"
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
    <string>$ROOT/scripts/sandbox_retry.py</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG_DIR/repush.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/repush.err</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
</dict>
</plist>
PLIST_END

plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "repush-job: installed $PLIST, running $ROOT/scripts/sandbox_retry.py"
echo "repush-job: daily at 08:00 local; log at $LOG_DIR/repush.log"
