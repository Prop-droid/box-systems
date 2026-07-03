#!/bin/bash
# Launches the LiteLLM proxy on 127.0.0.1:4000. Sources provider API keys from
# ~/.hermes/.env + the master key from ~/.config/litellm/litellm.env. DRY: no
# client currently points here; this is a metering proxy awaiting deliberate cutover.
set -uo pipefail
set -a
[ -f "$HOME/.hermes/.env" ] && . "$HOME/.hermes/.env"
[ -f "$HOME/.config/litellm/litellm.env" ] && . "$HOME/.config/litellm/litellm.env"
set +a
exec "$HOME/.local/bin/litellm" \
  --config "$HOME/systems/litellm/config.yaml" \
  --host 127.0.0.1 --port 4000
