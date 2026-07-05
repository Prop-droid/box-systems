# SSH key passphrase plan (SSH-2) — nothing applied

1. Encrypt all three: `id_ed25519_mac`, `id_ed25519_nobara`, `id_ed25519_github`.
   All are plaintext today (`ssh-keygen -y -P '' -f <key>` succeeds); box read = instant lateral move to Mac + Nobara + push to the private Prop-droid org.
2. Add a passphrase in place (keeps the same public key, so no re-authorizing on Mac/Nobara/GitHub):
   `for k in mac nobara github; do ssh-keygen -p -f ~/.ssh/id_ed25519_$k; done`
3. Use a distinct, strong passphrase per key; store them in your password manager, not on the box.
4. Agent setup so you type each once per login, not per use:
   `eval "$(ssh-agent -s)"` then `ssh-add ~/.ssh/id_ed25519_mac ~/.ssh/id_ed25519_nobara ~/.ssh/id_ed25519_github`
   (persist by enabling a `ssh-agent` user unit / adding the `eval` line to your shell rc — there is no user ssh-agent running now).
5. What breaks: any NON-interactive use (a future cron/headless job) will hang on the passphrase prompt unless the key was pre-added to a reachable agent (`SSH_AUTH_SOCK`). Verified today: no `~/systems` cron uses these keys, so nothing headless breaks now.
6. Interactive `ssh mac` / `ssh nobara` / `git push` to Prop-droid keep working once the key is in the agent for the session.
7. Caveat if you later add a headless git-push job: give it a dedicated deploy key (repo-scoped, its own agent socket via `GIT_SSH_COMMAND`) rather than reverting `id_ed25519_github` to plaintext.
8. Rollback: `ssh-keygen -p -f ~/.ssh/id_ed25519_<k>` and enter an empty new passphrase to strip it again.
