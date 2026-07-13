#!/bin/bash
# manifest-tool.sh
# Walks ~/outbox/, applies exclusions, and generates ~/outbox/.manifest.json

OUTBOX="$HOME/outbox"
MANIFEST="$OUTBOX/.manifest.json"

mkdir -p "$OUTBOX"

# Create a temporary file for the files array
TEMP_FILES=$(mktemp)

COUNT=0
TOTAL_BYTES=0

# Exclusions
EXCLUDE_OPTS=("-path" "$OUTBOX/.manifest.json" "-prune" "-o" "-name" ".git" "-prune" "-o" "-name" "node_modules" "-prune" "-o" "-name" ".venv" "-prune" "-o" "-name" "__pycache__" "-prune" "-o" "-name" "*.qcow2" "-prune" "-o" "-name" "id_*" "-prune" "-o" "-name" "*.pem" "-prune" "-o" "-name" ".env*" "-prune" "-o")

# Find files and compute sha256
find "$OUTBOX" "${EXCLUDE_OPTS[@]}" -type f -print0 | while IFS= read -r -d '' file; do
    rel_path="${file#$OUTBOX/}"
    bytes=$(stat -c%s "$file")
    sha=$(sha256sum "$file" | awk '{print $1}')
    
    # Append to temp file
    if [ $COUNT -gt 0 ]; then
        echo "," >> "$TEMP_FILES"
    fi
    printf '    {"path": "%s", "bytes": %d, "sha256": "%s"}' "$rel_path" "$bytes" "$sha" >> "$TEMP_FILES"
    
    COUNT=$((COUNT + 1))
    TOTAL_BYTES=$((TOTAL_BYTES + bytes))
    
    # We can't export COUNT and TOTAL_BYTES from a subshell directly, so we write to another temp file
    echo "$COUNT $TOTAL_BYTES" > "${TEMP_FILES}.stats"
done

if [ -f "${TEMP_FILES}.stats" ]; then
    read COUNT TOTAL_BYTES < "${TEMP_FILES}.stats"
    rm "${TEMP_FILES}.stats"
else
    COUNT=0
    TOTAL_BYTES=0
fi

TS=$(date -Iseconds)

cat > "$MANIFEST" <<EOF
{
  "v": 1,
  "node": "$HOSTNAME",
  "created": "$TS",
  "user": "$USER",
  "count": $COUNT,
  "total_bytes": $TOTAL_BYTES,
  "files": [
$(cat "$TEMP_FILES")
  ],
  "skipped": []
}
EOF

rm -f "$TEMP_FILES"
