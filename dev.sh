#!/usr/bin/env bash
# dev.sh — one entrypoint for the ~/systems estate (task 55).
#
# Make-style dispatcher over the box's dev/ops helpers so there is a single
# command to remember. Thin passthrough — each subcommand just execs the real
# script and forwards args/exit code.
#
#   dev doctor [args]   run box-doctor  (box-doctor/doctor.sh)
#   dev qa [args]       run the estate smoke test (qa/smoke.sh)
#   dev nq <args>       night-queue CLI passthrough (night-queue/nq)
#   dev hooks [args]    install/verify pre-commit hooks (hooks/install.sh)
#   dev help            this text
#
# Suggested: alias dev='bash ~/systems/dev.sh'   (or symlink onto PATH)
set -uo pipefail
SYS="$HOME/systems"

usage() {
  # print the contiguous header comment block (skip shebang, stop at first code line)
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$SYS/dev.sh"
}

cmd="${1:-help}"; shift 2>/dev/null || true
case "$cmd" in
  doctor) exec bash "$SYS/box-doctor/doctor.sh" "$@" ;;
  qa)     exec bash "$SYS/qa/smoke.sh" "$@" ;;
  nq)     exec "$SYS/night-queue/nq" "$@" ;;
  hooks)  exec bash "$SYS/hooks/install.sh" "$@" ;;
  help|-h|--help) usage ;;
  *) echo "dev: unknown command '$cmd'" >&2; echo >&2; usage >&2; exit 2 ;;
esac
