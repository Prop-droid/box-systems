# Shared env for the task-lessons loop. Source me; don't execute.
# Puts gbrain (bun-shebang .ts) on PATH and loads the embedding keys the way
# gbrain-weekly does. Safe to source repeatedly.
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
if [ -f "$HOME/.hermes/.env" ]; then
  GEMINI_API_KEY=$(grep -E "^GEMINI_API_KEY=" "$HOME/.hermes/.env" | cut -d= -f2-)
  GOOGLE_API_KEY=$(grep -E "^GOOGLE_API_KEY=" "$HOME/.hermes/.env" | cut -d= -f2-)
  export GEMINI_API_KEY GOOGLE_API_KEY
fi
export TASK_LESSONS_DIR="$HOME/systems/task-lessons"
