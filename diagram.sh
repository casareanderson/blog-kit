#!/usr/bin/env bash
# SVG -> 2x PNG, ready to embed in a post.
#
# Author at 880px wide and render at 1760: dev.to displays the image at roughly
# 800px, and the spare pixels are the difference between crisp type and soft
# type on a retina screen.
#
# Needs: librsvg2-bin  (apt-get install -y librsvg2-bin)
set -euo pipefail
src="${1:?usage: diagram.sh path/to/diagram.svg [width]}"
width="${2:-1760}"
out="${src%.svg}.png"
command -v rsvg-convert >/dev/null || {
  echo "rsvg-convert not found — apt-get install -y librsvg2-bin" >&2; exit 1; }
rsvg-convert -w "$width" "$src" -o "$out"
printf '%s  (%s bytes)\n' "$out" "$(stat -c %s "$out")"
