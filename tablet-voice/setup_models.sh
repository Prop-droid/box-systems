#!/bin/bash
# setup_models.sh: verify, and fetch when missing or wrong, the three openWakeWord v0.5.1 ONNX files that
# tablet-voice's wake re-check needs (14d section 1), by sha256. A good file is never touched; a download
# lands under a temporary name and is renamed in only after its sha256 matches. Also checks that
# faster-whisper base.en is in the local Hugging Face cache (the service loads it with local_files_only and
# HF_HUB_OFFLINE=1, so it never downloads at start). The openWakeWord models are CC BY-NC-SA 4.0 (personal use).
#
#   bash setup_models.sh                      # models/ next to this script
#   MODELS_DIR=/some/dir bash setup_models.sh
# Exit 0 = all three ONNX files verified and base.en present.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${MODELS_DIR:-$HERE/models}"
BASE="https://github.com/dscripka/openWakeWord/releases/download/v0.5.1"
declare -A SHA=(
  [melspectrogram.onnx]=ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f
  [embedding_model.onnx]=70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f
  [hey_jarvis_v0.1.onnx]=94a13cfe60075b132f6a472e7e462e8123ee70861bc3fb58434a73712ee0d2cb
)
mkdir -p "$DIR"
rc=0
for f in melspectrogram.onnx embedding_model.onnx hey_jarvis_v0.1.onnx; do
  want="${SHA[$f]}"
  if [ -f "$DIR/$f" ] && [ "$(sha256sum "$DIR/$f" | cut -d' ' -f1)" = "$want" ]; then
    echo "ok      $f"
    continue
  fi
  [ -f "$DIR/$f" ] && echo "BAD     $f (sha256 mismatch, fetching a fresh copy)"
  tmp="$(mktemp "$DIR/.$f.XXXXXX")"
  if curl -fsSL --max-time 120 -o "$tmp" "$BASE/$f" && [ "$(sha256sum "$tmp" | cut -d' ' -f1)" = "$want" ]; then
    chmod 644 "$tmp" && mv -f "$tmp" "$DIR/$f" && echo "fetched $f"
  else
    rm -f "$tmp"
    echo "FAIL    $f (download failed or sha256 mismatch)"
    rc=1
  fi
done
HUB="${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}"
if compgen -G "$HUB/models--Systran--faster-whisper-base.en/snapshots/*/model.bin" >/dev/null; then
  echo "ok      faster-whisper base.en ($HUB)"
else
  echo "MISSING faster-whisper base.en in $HUB; fetch it once with:"
  echo "        HF_HUB_OFFLINE=0 $HERE/.venv/bin/python -c 'from faster_whisper import download_model; download_model(\"base.en\")'"
  rc=1
fi
exit $rc
