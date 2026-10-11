#!/usr/bin/env bash
# Headless Electron startup: exercise the packaged wrapper, libraries and GUI.
set -euo pipefail
package="${1:?pass the built package path}"
test -x "$package/bin/t3code"
test -s "$package/share/applications/t3code.desktop"
grep -q 'Exec=t3code' "$package/share/applications/t3code.desktop"
profile="$(mktemp -d)"
trap 'rm -rf "$profile"' EXIT
set +e
env -u ELECTRON_RUN_AS_NODE -u WAYLAND_DISPLAY -u VITE_DEV_SERVER_URL \
  T3CODE_HOME="$profile/t3" T3CODE_DISABLE_AUTO_UPDATE=1 \
  XDG_CONFIG_HOME="$profile/config" XDG_DATA_HOME="$profile/share" \
  XDG_CACHE_HOME="$profile/cache" timeout 20s xvfb-run -a "$package/bin/t3code" --ozone-platform=x11 --no-sandbox --disable-gpu \
  --enable-logging=stderr --user-data-dir="$profile/data" >"$profile/startup.log" 2>&1
status=$?
set -e
cat "$profile/startup.log"
if [[ "$status" != 124 ]]; then
  echo "T3 Code exited during startup (status $status)" >&2
  exit 1
fi
if grep -Ei 'error while loading shared libraries|FATAL:|Trace/breakpoint trap|Segmentation fault' "$profile/startup.log"; then
  exit 1
fi
if ! grep -q 'main window created' "$profile/startup.log"; then
  echo 'Main window never reached ready state' >&2
  exit 1
fi
echo 'Headless startup passed (application remained running for 20 seconds)'
