# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A desktop-pet-style game built on pygame: an NPC pet with hunger/thirst/boredom needs, driven by a small PyTorch DQN (deep Q-network) agent that learns to walk toward whatever target the pet currently needs (the mouse cursor, food, water, or a toy). The long-term goal is a cross between a desktop pet and an actual game — feeding/playing interactions, and eventually per-pet personality affecting how it behaves toward the player and other NPCs.

## Commands

There is no build system, package manifest, or test suite — run scripts directly with the venv's Python.

```bash
# Run the game (opens a window; move the mouse around, click "Toy" to drop a toy)
.venv/bin/python virt-pet.py
```

The `.venv` directory (Python 3.14) already has `pygame`, `torch`, and `numpy` installed. There is no `requirements.txt`; if adding dependencies, install them into `.venv` with `.venv/bin/pip install <pkg>`.

There's no automated test suite. The working pattern used throughout development is a quick headless smoke test: `pygame.init()` + `set_mode(...)`, construct the objects, call `.update()` in a loop with synthetic inputs, and assert on the resulting state (e.g. `pet.hunger`, `pet.target_pos`, `pet.active_need`). This works even without a display attached (SDL still needs `pygame.display.set_mode()` called once).

## Architecture

- **`virt-pet.py`** — pygame entry point and the only place that owns the game loop, event handling, and drawing. Each frame it: polls events (including the toy button click), draws `food`/`water`/`toy` items and stat bars, reads the mouse position, and calls `pet.update(dt, mouse_pos, food.pos, water.pos, toy_pos)`. The toy is inactive (`toy.active = False`, not drawn, `toy_pos=None`) until the "Toy" button (top-right) is clicked, which activates it and drops it at a random ground position.
- **`npc.py`** — the `npc` class, the pet itself. This is where nearly all the game logic lives:
  - **Needs**: `hunger`, `thirst`, `boredom` each climb every frame at their own rate, capped at 100, and drain when the pet is within `interact_radius` of the corresponding item (food/water/toy).
  - **Target selection** (`choose_target`): decides what the pet is currently walking toward. Uses hysteresis via `self.active_need` — once a need crosses its seek threshold (e.g. `hunger_threshold`) and becomes the active pursuit, the pet keeps heading for that item even if the value dips back under the threshold, until it drops below `satiated_threshold` (default 5). Falls back to the mouse cursor when no need is urgent. This is the mechanism to extend if more needs/items are added later.
  - **Personality**: `open`/`conscient`/`extravers`/`agreeable`/`neuroticism` (Big Five, 0-10 scale), randomized per-instance in `randomize_personality()` (called from `__init__`, so every `npc(...)` gets different values). **Not wired into behavior yet** — reserved for future NPC/player interaction logic (e.g. extraversion affecting how readily the pet approaches others). All the needs-related thresholds/rates (`hunger_threshold`, `eat/interact_radius`, drain rates, etc.) are already per-instance attributes for the same reason: different pets can eventually be tuned differently without touching the update logic.
  - **Movement/RL**: `update()` still runs the same DQN loop established early on — build a 4-value state `[pet.x, pet.y, target.x, target.y]` (normalized 0-1), get an action from `self.agent` (0: left, 1: stay, 2: right), move, then reward *only* reflects the pet's own contribution to closing the distance (measured before/after its own move against the same frozen `target_pos`), not the target moving on its own. Training happens online, every frame, via `agent.remember()` + `agent.replay()` — there's no separate training script or offline loop.
- **`items.py`** — the `item` class for food/water/toy. `pos` is always the item's ground-contact point (equivalent to `midbottom`), not its center — food/water use `rect.midbottom = pos`, and the toy circle's center is offset up by its radius to match that convention. Add new item types by extending `COLORS` and the `if/elif` chain in `draw()`.
- **`npc_net.py`** — self-contained DQN implementation (`QNetwork`: 2 hidden layers of 64, `NPCAgent`: experience replay + target network + epsilon-greedy). No pygame/game-specific code here; it's a generic small DQN agent that `npc.py` drives.

Key constants live at the top of `npc.py` (gravity/ground, need rates/thresholds/drain rates, RL state/action sizes) — most have a corresponding per-instance attribute set in `npc.__init__` for future per-pet tuning.
