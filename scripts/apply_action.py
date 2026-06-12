#!/usr/bin/env python3
"""Apply a registration/admin action to data.json.

Driven entirely by environment variables set from workflow_dispatch inputs:
  ACTION      register | pair | create_tournament | add_group | lock | unlock | remove
  TOURNAMENT  tournament id
  GROUP       group id (optional for pair: blank = all doubles groups)
  PLAYER      player name
  PARTNER     partner name (doubles, optional)
  PIN         admin pin supplied by caller (admin actions only)
  ADMIN_PIN   secret pin from repo settings
  NAME        new tournament / group name
  DATE        new tournament date (YYYY-MM-DD)
  GROUPS      comma-separated category names for create_tournament
"""
import json
import os
import random
import re
import sys
from datetime import datetime, timezone

DATA_FILE = "data.json"

ADMIN_ACTIONS = {"pair", "create_tournament", "add_group", "lock", "unlock", "remove"}


def fail(msg):
    print(f"::error::{msg}")
    sys.exit(1)


def env(key):
    return (os.environ.get(key) or "").strip()


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def group_type(name):
    return "doubles" if "doubles" in name.lower() else "singles"


def main():
    action = env("ACTION")
    t_id = env("TOURNAMENT")
    g_id = env("GROUP")
    player = env("PLAYER")
    partner = env("PARTNER")
    pin = env("PIN")
    admin_pin = env("ADMIN_PIN")
    name = env("NAME")
    date = env("DATE")
    groups_csv = env("GROUPS")

    with open(DATA_FILE) as f:
        data = json.load(f)

    if action in ADMIN_ACTIONS:
        if not admin_pin:
            fail("ADMIN_PIN secret is not configured in the repository")
        if pin != admin_pin:
            fail("Invalid admin PIN")

    def find_tournament():
        for t in data["tournaments"]:
            if t["id"] == t_id:
                return t
        fail(f"Tournament not found: {t_id}")

    def find_group(t):
        for g in t["groups"]:
            if g["id"] == g_id:
                return g
        fail(f"Group not found: {g_id}")

    def find_entry(g, nm):
        nm = nm.casefold()
        for e in g["entries"]:
            if e["player"].casefold() == nm or (e.get("partner") or "").casefold() == nm:
                return e
        return None

    if action == "register":
        if not player:
            fail("Player name is required")
        t = find_tournament()
        if t.get("status") == "locked":
            fail("Registrations are locked for this tournament")
        g = find_group(t)
        if find_entry(g, player):
            fail(f"{player} is already registered in {g['name']}")
        if g["type"] == "singles" or not partner:
            g["entries"].append({"player": player, "partner": None, "paired_by": None})
        else:
            if player.casefold() == partner.casefold():
                fail("You cannot partner with yourself")
            existing = find_entry(g, partner)
            if existing:
                if existing.get("partner"):
                    fail(f"{partner} is already paired in {g['name']}")
                existing["partner"] = player
                existing["paired_by"] = "self"
            else:
                g["entries"].append({"player": player, "partner": partner, "paired_by": "self"})

    elif action == "pair":
        t = find_tournament()
        targets = [
            g for g in t["groups"]
            if g["type"] == "doubles" and (not g_id or g["id"] == g_id)
        ]
        paired_count = 0
        for g in targets:
            singles = [e for e in g["entries"] if not e.get("partner")]
            random.shuffle(singles)
            while len(singles) >= 2:
                a = singles.pop()
                b = singles.pop()
                a["partner"] = b["player"]
                a["paired_by"] = "random"
                g["entries"].remove(b)
                paired_count += 1
        print(f"Created {paired_count} random pair(s)")

    elif action == "create_tournament":
        if not name:
            fail("Tournament name is required")
        new_id = slugify(name)
        if any(t["id"] == new_id for t in data["tournaments"]):
            fail(f"A tournament named '{name}' already exists")
        groups = []
        for gname in [x.strip() for x in groups_csv.split(",") if x.strip()]:
            groups.append({
                "id": slugify(gname),
                "name": gname,
                "type": group_type(gname),
                "entries": [],
            })
        data["tournaments"].append({
            "id": new_id,
            "name": name,
            "date": date or None,
            "status": "open",
            "groups": groups,
        })

    elif action == "add_group":
        if not name:
            fail("Group name is required")
        t = find_tournament()
        new_id = slugify(name)
        if any(g["id"] == new_id for g in t["groups"]):
            fail(f"Group '{name}' already exists in {t['name']}")
        t["groups"].append({
            "id": new_id,
            "name": name,
            "type": group_type(name),
            "entries": [],
        })

    elif action in ("lock", "unlock"):
        t = find_tournament()
        t["status"] = "locked" if action == "lock" else "open"

    elif action == "remove":
        if not player:
            fail("Player name is required")
        t = find_tournament()
        g = find_group(t)
        e = find_entry(g, player)
        if not e:
            fail(f"{player} not found in {g['name']}")
        nm = player.casefold()
        if e["player"].casefold() == nm:
            if e.get("partner"):
                # keep the partner as an unpaired entry
                e["player"] = e["partner"]
                e["partner"] = None
                e["paired_by"] = None
            else:
                g["entries"].remove(e)
        else:
            # removing the partner half of a pair
            e["partner"] = None
            e["paired_by"] = None

    else:
        fail(f"Unknown action: {action}")

    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Applied action '{action}'")


if __name__ == "__main__":
    main()
