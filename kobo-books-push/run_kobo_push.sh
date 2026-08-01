#!/bin/bash
# Flat-copy every ebook from the Calibre library (~/books) into the personal
# Google Drive "Rakuten Kobo" folder, which the Kobo e-reader syncs from.
# Copy-only: never deletes anything on the Drive side. The Kobo folder is
# flat, so files land by basename regardless of Calibre's Author/Title dirs.
set -euo pipefail
LIB="$HOME/books"
DEST="gdrive-personal:Rakuten Kobo"
LOG="$HOME/systems/kobo-books-push/last_run.log"

{
  echo "=== kobo-books-push $(date -Is) ==="
  # Existing remote sizes: Calibre renames imported files, so name comparison
  # can't dedupe against books that were already in the Drive folder under
  # their original filenames. Identical content = identical size; skip those.
  remote_sizes="$(rclone lsjson --files-only "$DEST" | python3 -c 'import json,sys; print("\n".join(str(f["Size"]) for f in json.load(sys.stdin)))')"
  find "$LIB" -type f \( -iname '*.epub' -o -iname '*.pdf' \) | while IFS= read -r f; do
    size=$(stat -c%s "$f")
    if grep -qx "$size" <<< "$remote_sizes"; then
      echo "skip (already on Drive): $(basename "$f")"
      continue
    fi
    rclone copy --no-traverse "$f" "$DEST" 2>&1
    echo "pushed: $(basename "$f")"
  done
  echo "=== done $(date -Is) ==="
} > "$LOG" 2>&1
