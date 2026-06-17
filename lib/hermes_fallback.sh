# Shared LLM fallback: when a headless `claude -p` cron run fails, retry the
# same prompt through Hermes before giving up. Source me, then call
# hermes_fallback after a failed claude attempt.
#
#   hermes_fallback <prompt_file> <out_file> <err_file>
#     -> 0 and writes the Hermes answer to <out_file> if Hermes succeeded
#     -> non-zero (and leaves <out_file> untouched/empty) otherwise
#
# Hermes routes via its own configured model chain (Codex primary, Gemini
# fallbacks) -- we deliberately do NOT pin -m here. Cost note: this spends paid
# provider tokens unattended, so it only fires on an actual claude failure.
# Override the cap with HERMES_FALLBACK_TIMEOUT (seconds, default 1500).

hermes_fallback() {
  local pf="$1" of="$2" ef="${3:-/dev/null}"
  # hermes lives in ~/.local/bin; don't depend on the caller's PATH.
  case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac
  command -v hermes >/dev/null 2>&1 || return 1
  [ -s "$pf" ] || return 1
  echo ">> claude failed; trying hermes fallback ..." >&2
  local tmp; tmp="$(mktemp)"
  if timeout "${HERMES_FALLBACK_TIMEOUT:-1500}" \
        hermes -z "$(cat "$pf")" --yolo >"$tmp" 2>>"$ef" && [ -s "$tmp" ]; then
    mv -f "$tmp" "$of"
    echo ">> hermes fallback succeeded" >&2
    return 0
  fi
  rm -f "$tmp"
  echo ">> hermes fallback also failed" >&2
  return 1
}
