#!/usr/bin/python3
# wallet.py
#
# The player's currency - explicitly NOT tied to any individual pet. A
# player may have several pets (see npc.py's per-name saves/<name>.json)
# and switch between them via Load; currency follows the player, not
# whichever pet happens to be active, so it lives in its own file entirely
# separate from per-pet persistence.

import json
import os

WALLET_PATH = os.path.join(os.path.dirname(__file__), "wallet.json")


class Wallet:
    def __init__(self):
        self.currency = 0
        self.load()

    def earn(self, amount):
        self.currency += amount
        self.save()

    def save(self):
        with open(WALLET_PATH, "w") as f:
            json.dump({"currency": self.currency}, f, indent=2)

    def load(self):
        try:
            with open(WALLET_PATH) as f:
                data = json.load(f)
            self.currency = data.get("currency", 0)
        except FileNotFoundError:
            pass
