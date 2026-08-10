#!/usr/bin/env python3
"""Monthly tax task -> personal Google Tasks (propeidzas), PERSONAL list.

The Google Tasks API cannot set recurrence (UI-only), so the systemd timer IS
the recurrence: it fires on the 27th of each month and this script inserts one
task due that day. Idempotent — re-running (or a Persistent=true catch-up after
the box was off) will not create a duplicate for the same due date.

Creds: /home/tomas/tablet-assistant/token_personal.json (tasks scope, refreshed
in place). Run with /home/tomas/tablet-assistant/venv/bin/python.
"""
import datetime as dt
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN = "/home/tomas/tablet-assistant/token_personal.json"
TASKLIST = "MTE1NjY1MTM5OTk5NjU5MTU3NTE6MDow"  # PERSONAL
TITLE = "Sutvarkyti mokesčius"

# Lithuanian month names in the genitive ("už 2026 m. liepos mėn.").
MONTHS_GEN = [
    "sausio", "vasario", "kovo", "balandžio", "gegužės", "birželio",
    "liepos", "rugpjūčio", "rugsėjo", "spalio", "lapkričio", "gruodžio",
]


def main():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if not creds.valid:
        creds.refresh(Request())
        with open(TOKEN, "w") as fh:
            fh.write(creds.to_json())
    svc = build("tasks", "v1", credentials=creds)

    today = dt.date.today()
    # Due date = the 27th of the current month (the day the timer fires).
    due_date = today.replace(day=27)
    due = due_date.strftime("%Y-%m-%dT00:00:00.000Z")

    existing = svc.tasks().list(
        tasklist=TASKLIST, showCompleted=True, showHidden=True, maxResults=100
    ).execute().get("items", [])
    for t in existing:
        if t.get("title") == TITLE and (t.get("due") or "").startswith(due_date.isoformat()):
            print(f"already exists: {t['id']}")
            return 0

    prev = (due_date.replace(day=1) - dt.timedelta(days=1))
    task = svc.tasks().insert(
        tasklist=TASKLIST,
        body={
            "title": TITLE,
            "notes": (
                "Mėnesio mokesčiai: deklaruoti ir sumokėti už "
                f"{prev.year} m. {MONTHS_GEN[prev.month - 1]} mėn."
            ),
            "due": due,
        },
    ).execute()
    print(f"created: {task['id']} due {due_date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
