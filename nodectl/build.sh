#!/bin/bash
set -euo pipefail

TAILWIND_BIN=./tailwindcss-linux-x64

check_sha256() {
    local expected="$1"
    local path="$2"
    local actual
    actual="$(sha256sum "$path" | awk '{print $1}')"
    if [[ "$actual" != "$expected" ]]; then
        echo "Checksum mismatch for $path" >&2
        echo "expected: $expected" >&2
        echo "actual:   $actual" >&2
        exit 1
    fi
}

require_file() {
    local path="$1"
    if [[ ! -f "$path" ]]; then
        echo "Required asset missing: $path" >&2
        exit 1
    fi
}

require_file "$TAILWIND_BIN"
require_file static/input.css
require_file static/vendor/htmx.min.js
require_file static/vendor/xterm.css
require_file static/vendor/xterm.js
require_file static/vendor/xterm-addon-fit.js

check_sha256 5036c4fb4328e0bcdbb6065c70d8ac9452e0d4c947113a788a8f94fd390425c1 "$TAILWIND_BIN"
check_sha256 b3bdcf5c741897a53648b1207fff0469a0d61901429ba1f6e88f98ebd84e669e static/vendor/htmx.min.js
check_sha256 832f3f2c603b43ad4351ff04970150cc7a873014276db126a6065c6dd81e4872 static/vendor/xterm.css
check_sha256 f0aea0f75f48559013ae6643c2479dd737d26da42d5524e6d2b70915ae6523c7 static/vendor/xterm.js
check_sha256 10f3194c5f17c1786fb7d5db865c1ec8539b6736a318063fd38bdaaf7c46848f static/vendor/xterm-addon-fit.js

chmod +x "$TAILWIND_BIN"
"$TAILWIND_BIN" -i static/input.css -o static/output.css --minify

echo "Build complete."
