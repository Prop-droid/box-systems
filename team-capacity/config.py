"""Team-capacity config. Facts only; behaviour flags live in settings.json next to this file."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
TZ = "Europe/Vilnius"
LIST_ID = "901110066469"
TEAM_ID = "9011638245"
TOMAS_UID = 81523916
POOL = {"IGN": 81523940, "LEO": 81542515, "AGU": 81523936, "PAO": 81523945,
        "KAR": 87386337, "MAR": 87404945, "ANA": 81523938, "AYC": 81523925}
U2C = {v: k for k, v in POOL.items()}
NAMES = {"IGN": "Ignacio", "LEO": "Leonardo", "AGU": "Agustina", "PAO": "Paolo",
         "KAR": "Karen", "MAR": "Marcos", "ANA": "Anastasiia", "AYC": "Aicha"}
NAME_HINTS = {"IGN": ["ignacio"], "LEO": ["leonardo", "leo "], "AGU": ["agustina", "agus"], "PAO": ["paolo"],
              "KAR": ["karen"], "MAR": ["marcos"], "ANA": ["anastasiia", "anastasia"], "AYC": ["aicha", "ayca", "ayça"]}
F_VIDEO_EDITOR = "f3d819ab-1db7-4bfb-a3d2-3a7200939722"
F_DESIGNER = "71125236-4e60-4363-9d04-e64780b2d8f2"
F_DELIVERABLE_TYPE = "dba1ec3e-ef43-449c-bfea-3990a75d0c6f"
F_FILE_LINK = "10f8654f-bae1-4de3-8114-6f7b4eac7908"
F_APPLOVIN_LINK = "94c5fbec-d373-4dc1-a81a-e214a42bfb58"
REMAINING_FIELD_NAME = "Remaining h"
DELIVERABLE_ITEM_ID = 1013
# Status vocabulary (lowercase, exactly as ClickUp returns)
S_LIVE = "in progress"; S_QUEUE = "to do"; S_FIX = "needs fixing"; S_BACKLOG = "backlog"
HANDOFF = {"cs review", "approved", "sent to mb", "mb - testing"}   # first entry = finished (Tomas 2026-10-27)
MID = {"in progress", "cs review", "needs fixing"}
CAP_H = 36.0; DAY_H = 7.2; HALF_DAY_H = 3.6
HOLIDAY_FEEDS = {"IGN": "en.ar", "AGU": "en.ar", "KAR": "en.ar", "MAR": "en.ar",
                 "LEO": "en.co", "PAO": "en.philippines", "AYC": "en.turkish", "ANA": "en.lithuanian"}
FEED_SUFFIX = "#holiday@group.v.calendar.google.com"
OOO_WORDS = ("ooo", "out of office", "day off", "days off", "vacation", "holiday", "sick", "leave", "pto", "off work")
PROJ_W = {"mid": 0.7, "todo_due": 0.5}  # approved/cs review already count as finished (handoff rule)
DEFAULT_EST_H = {"img": 2.5, "vid": 8.0}
DISCORD_CHANNEL = "1531648564932120737"; DISCORD_TOKEN_VAR = "CREATIVE_TOKEN"
CLAUDE_BIN = "/usr/local/bin/claude-max"
GWS = os.path.expanduser("~/.local/bin/gws-work")
LEDGER_DIR = os.path.join(HERE, "ledger"); REPORT_DIR = os.path.join(HERE, "reports"); STATE = os.path.join(HERE, "state.json")
GATE_LOG = os.path.join(HERE, "gate.log")

def settings():
    p = os.path.join(HERE, "settings.json")
    d = {"writes": False, "post_team": False, "doc_id": None, "sheet_id": None}
    if os.path.exists(p):
        d.update(json.load(open(p)))
    return d
