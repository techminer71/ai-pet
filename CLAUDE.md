# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A virtual pet / NPC simulation built on pygame, with a PyTorch DQN (deep Q-network) agent intended to eventually drive NPC behavior. The project is in early prototype stage: the game loop and the RL agent are not yet wired together.

## Commands

There is no build system, package manifest, or test suite — run scripts directly with the venv's Python.

```bash
# Run the pygame demo (opens a window, moves the NPC on screen)
.venv/bin/python virt-pet.py

# Run the standalone DQN agent training loop (mock environment, no game integration yet)
.venv/bin/python npc_net.py
```

The `.venv` directory (Python 3.14) already has `pygame`, `torch`, and `numpy` installed. There is no `requirements.txt`; if adding dependencies, install them into `.venv` with `.venv/bin/pip install <pkg>`.

## Architecture

- `virt-pet.py` — pygame entry point. Owns the game loop: event polling, screen clear/fill, drawing, and calling `npc.update(dt)` each frame. `dt` is delta time in seconds, used for framerate-independent movement.
- `npc.py` — the `npc` class representing an on-screen character. Holds position (`pygame.Vector2`), vertical velocity, and grounded state. `update(dt)` currently applies simple gravity/jump physics and picks a **random** horizontal move direction each frame (`rand.random()` threshold, not yet driven by the RL agent).
- `npc_net.py` — a self-contained DQN implementation (`QNetwork` + `NPCAgent`) with experience replay, target network, and epsilon-greedy exploration. Its `main()` runs a mock training loop with hardcoded state transitions as a placeholder — it does not yet call into `virt-pet.py`/`npc.py`. Connecting `NPCAgent.act()` to `npc.update()` (replacing the random move logic) is the natural integration point once state/reward/action definitions are finalized.

Key constants live directly in `npc.py`: `GRAVITY`, `JUMP_FORCE`, `GROUND_Y` (currently `720`, matching the window height in `virt-pet.py`) — keep these in sync if the window size changes.
