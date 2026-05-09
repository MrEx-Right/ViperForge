#!/usr/bin/env bash
# ─────────────────────────────────────────────
#  ViperForge — Red Team Exploit Factory
#  Launcher Script
# ─────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="$SCRIPT_DIR/viperforge"
SOURCE="$SCRIPT_DIR/main.go"

# ── Build if binary is missing or source is newer ──────────────────────────
if [ ! -f "$BINARY" ] || [ "$SOURCE" -nt "$BINARY" ]; then
    echo "[*] Building ViperForge..."
    cd "$SCRIPT_DIR"
    go build -o "$BINARY" . || {
        echo "[-] Build failed. Make sure Go is installed and in your PATH."
        exit 1
    }
    echo "[+] Build successful."
fi

# ── Launch ──────────────────────────────────────────────────────────────────
exec "$BINARY" "$@"
