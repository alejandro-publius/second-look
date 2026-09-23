#!/usr/bin/env bash
# Install the launchd job that re-pushes our records to the shared sandbox at 08:00 on Sep 28,
# Sep 30 and Oct 1 (Update 14 section 6 item 3), logging to ~/second-look-backups/repush.log.
#   bash scripts/install_repush_job.sh            -> installs and loads the job
#   bash scripts/install_repush_job.sh --remove   -> unloads and removes it
# launchd repeats a calendar date every year, so scripts/repush_scheduled.sh checks the year too.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.secondlook.repush"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/second-look-backups/repush.log"

if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "repush-job: removed"
  exit 0
fi

day() { echo "<dict><key>Month</key><integer>$1</integer><key>Day</key><integer>$2</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>"; }
mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
cat > "$PLIST" <<PLIST_END
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ROOT/scripts/repush_scheduled.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <array>
    $(day 9 28)
    $(day 9 30)
    $(day 10 1)
  </array>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
</dict>
</plist>
PLIST_END

plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "repush-job: installed $PLIST, running $ROOT/scripts/repush_scheduled.sh"
echo "repush-job: 08:00 local on Sep 28, Sep 30 and Oct 1; log at $LOG"
