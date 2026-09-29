#!/usr/bin/env bash
# Regenerate the favicon PNG set and the Open Graph card from their sources:
#   assets/icons/favicon.svg  (the mark; PNGs are rendered from the same geometry)
#   assets/og/og-card.html    (1200x630 social card; loads Google Fonts)
# Requires Google Chrome (headless) and Pillow in the active Python.
#   bash scripts/site/render_brand_assets.sh [python]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${1:-python3}"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

shot() { # width height url out [extra flags...]
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size="$1,$2" "${@:5}" --screenshot="$4" "$3" >/dev/null 2>&1
}

icon() { # size radius out
  cat > "$TMP/icon.html" <<EOF
<!doctype html><html><head><style>html,body{margin:0;background:transparent}svg{display:block;width:$1px;height:$1px}</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="$2" fill="#263221"/><circle cx="32" cy="32" r="17" fill="none" stroke="#f4efe6" stroke-width="5"/><circle cx="32" cy="32" r="6.5" fill="#a86131"/></svg>
</body></html>
EOF
  shot "$1" "$1" "file://$TMP/icon.html" "$TMP/$3" --default-background-color=00000000
}

icon 32 14 favicon-32.png          # rounded, transparent corners
icon 180 0 apple-touch-icon.png    # full-bleed: iOS applies its own mask
icon 192 0 icon-192.png            # full-bleed: manifest "maskable"
icon 512 0 icon-512.png
shot 1200 630 "file://$ROOT/assets/og/og-card.html" "$TMP/sentinel-og.png" --virtual-time-budget=8000

"$PY" - "$TMP" "$ROOT" <<'EOF'
import os, sys
from PIL import Image
tmp, root = sys.argv[1], sys.argv[2]
targets = {
    "favicon-32.png": "assets/icons", "apple-touch-icon.png": "assets/icons",
    "icon-192.png": "assets/icons", "icon-512.png": "assets/icons", "sentinel-og.png": "assets/og",
}
for name, folder in targets.items():
    im = Image.open(os.path.join(tmp, name))
    if name == "favicon-32.png":
        q = im.quantize(colors=32, method=Image.Quantize.FASTOCTREE)
    else:  # flat-colour artwork: a small palette is visually lossless
        q = im.convert("RGB").quantize(colors=64 if name.endswith("og.png") else 32,
                                       method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = os.path.join(root, folder, name)
    q.save(out, optimize=True)
    print(f"{out}: {os.path.getsize(out)} bytes")
EOF
