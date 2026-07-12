# Estate pre-commit hooks

Shared `pre-commit` hook for the box's git repos (`~/systems`, `~/personal/*`).
Self-contained — no gitleaks / git-secrets / pre-commit framework. Task 55, wave-5.

## Checks (against staged changes only)

| Check | Level | What it does |
|-------|-------|--------------|
| secret-scan | BLOCKING | Added lines matching known key/token patterns (AWS, GCP/private-key, Google API, OpenAI/Anthropic `sk-`, GitHub `ghp_`/PAT, Slack, ClickUp `pk_`, generic `secret=…`). |
| large-file  | BLOCKING | Staged blobs over `HOOK_MAX_BYTES` (default 5 MB). |
| shellcheck  | WARNING  | Staged `*.sh` linted at `-S warning`. Never blocks. Skipped with a note if `shellcheck` is not installed. |

## Install

```
bash ~/systems/hooks/install.sh          # default set: ~/systems + git repos under ~/personal
bash ~/systems/hooks/install.sh --check   # report status, change nothing
bash ~/systems/hooks/install.sh /path/repo
# or via the estate entrypoint:
bash ~/systems/dev.sh hooks [--check]
```

Install symlinks `<repo>/.git/hooks/pre-commit -> ~/systems/hooks/pre-commit`, so
this file is the single source of truth. A pre-existing non-symlink hook is
backed up to `pre-commit.pre-hooks.bak`. `.git/hooks/` is not version-controlled,
so re-run `install.sh` after cloning the repo fresh.

## Escape hatches

- Bypass all checks once: `git commit --no-verify`
- Allowlist one line: append `# pragma: allowlist secret` to it
- Allowlist patterns per repo: add ERE lines to `<repo>/.secrets-allowlist`
- Shared allowlist: `~/systems/hooks/secrets-allowlist.txt`
- Raise size ceiling once: `HOOK_MAX_BYTES=20000000 git commit ...`

## Notes

- `shellcheck` is not installed on the box today, so the lint step currently
  self-skips with a note. Install it (`apt-get install shellcheck`) to activate
  the warning-level lint — no hook change needed.
