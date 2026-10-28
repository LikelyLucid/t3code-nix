#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
nixfmt --check flake.nix nix/*.nix
statix check .
deadnix --fail .
actionlint
python3 -m unittest discover -s tests -v
nix flake check --no-warn-dirty --print-build-logs
