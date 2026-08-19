# AI Pet

A little desktop pet built with pygame. It has needs (hunger, thirst, boredom, tiredness) and a happiness meter, and a small PyTorch reinforcement-learning agent that learns, live as you play, to walk toward whatever it currently needs — food, water, its toy, or wherever you've called it. When nothing's urgent, it doesn't just freeze: it wanders, naps on its bed, plays fetch by itself, or brings the toy to you, in a mix shaped by its own (randomized, persisted) personality. Progress (its trained brain and personality) saves per pet name, so it picks up where it left off next time.

The goal is something between a desktop pet and an actual game: feed it, throw its toy for it, pet it, and watch it get better at navigating toward the things it wants — and act like it wants them, not just react to a meter crossing a threshold. Fetch is the first place that loop pays off directly: play it well and you earn currency, with cosmetics to spend it on planned next.

## Features

- **Needs-driven behavior** — hunger, thirst, boredom, and tiredness each rise over time; the pet automatically goes to handle whichever is most urgent - food, water, or its toy, and for tiredness, its actual bed, where it sleeps (with a "ZzZzZz" bubble) rather than just stopping in place.
- **Self-initiated idle behavior** — otherwise, instead of standing frozen, the pet picks something to do on its own: loiter, wander somewhere, go nap on its bed, grab a toy out of the toybox, throw a toy for itself and play, or bring one to your cursor for a game of fetch. *Which* it tends to pick is weighted by its Big Five personality traits (e.g. more agreeable/extraverted → more fetch, more conscientious → more napping) — the first real hook from personality into behavior. Right-click and choose "Call" to override it and bring the pet to you.
- **You can teach it fetch** — fetch isn't just a fixed odds roll: petting the pet (right-click → "Pet") shortly after it brings a toy back reinforces fetch as a favorite over playing alone, a little more each time; stop reinforcing it and that preference fades again over a few minutes. A taught habit, not a permanent toggle.
- **Fetch is a scored mini-game with real currency** — every successful delivery earns coins (shown top-right), whether the pet fetched on its own or you commanded it (right-click → "Fetch", which grabs a toy from the toybox first if none's out). Consecutive deliveries build a streak that stays flat for the first couple, then ramps up fast, so a deliberate streak pays a lot more than scattered one-offs — and commanding a round pays more than an autonomous one. The currency belongs to you, not any one pet, so it carries over across pets and sessions (see `wallet.py`).
- **Vocalizations** — the pet pops up a speech bubble (onomatopoeia + an emotion emoji) at meaningful moments: a happy bark when petted, called over, or starting to play; a whine when it wants something and you've been ignoring it a while; a growl if it's been neglected badly enough to be genuinely upset (angry, not whiny — angry dogs don't whine); a lonely howl when it's just been alone too long — and a "ZzZzZz" sleep bubble whenever it's actually resting at its bed, which silences the rest (no growling in its sleep). Vocabulary is per-species (currently just the dog/Corgi) so a future cat or robot gets its own sounds instead of barking.
- **Reinforcement learning** — a DQN agent (PyTorch) learns the actual walking policy live, no pretraining required. It gets less random and more purposeful the longer you play.
- **Happiness** — a separate meter that drifts down when the pet is ignored and rises from playing or petting it (right-click → "Pet").
- **Throwable toys, with real control** — pick a Ball or Bone from the toybox menu to bring it out (picking a different one swaps it; picking the same one again puts it away), then click it to throw it: which half you click sets the direction (right half throws left, and vice versa) and how close to the edge you click sets the power. Real physics: gravity, bouncing off the ground (1-2 times) and off the walls/ceiling. Ball and Bone play identically for now — same throw/fetch/self-play mechanics, just a different look.
- **Click to feed/water** — click the food or water item to satisfy that need instantly, wherever the pet is.
- **Animated sprite** — a walking/idle/sitting corgi (placeholder art, see [Assets](#assets)).
- **Save/load** — name a pet, and it's saved under that name; load a different saved pet anytime from the in-game pause menu.

## Requirements

- Python 3.14
- [pygame](https://www.pygame.org/), [PyTorch](https://pytorch.org/), [NumPy](https://numpy.org/)

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install pygame torch numpy
```

## Run

```bash
.venv/bin/python virt-pet.py
```

You'll land on a menu to name your pet and start. Naming a pet that already has a save resumes it (same trained brain, same personality) instead of starting fresh.

## Controls

See [`CONTROLS.txt`](CONTROLS.txt) for the full, current control scheme. Short version: right-click for a menu to Call the pet over, pet it, or command a Fetch round; click the toybox to bring a toy out (click it again to put it away), click a toy to throw it - which half you click controls direction, how close to the edge controls power - and press Esc to pause (save/load/back to menu from there).

## Project layout

| File | Purpose |
|---|---|
| `virt-pet.py` | Entry point — the game loop, menus, and rendering |
| `npc.py` | The pet itself: needs, target selection, the RL loop, sprite animation, save/load |
| `npc_net.py` | The DQN agent (generic, no game-specific code) |
| `items.py` | Food, water, bed, toybox, and the toy (kinds: ball/bone, including throw physics) |
| `vocalizations.py` | Per-species speech-bubble vocabulary (bark/growl/whine/howl) |
| `wallet.py` | The player's currency - not tied to any one pet (see `wallet.json`) |
| `CONTROLS.txt` | Up-to-date control reference |
| `DogBundle/` | Sprite assets (only the Corgi is currently used) |
| `saves/` | Per-pet save data (created at runtime, not checked in) |
| `wallet.json` | Player currency save data (created at runtime, not checked in) |

## Assets

`DogBundle/PNGs/Corgi.png` is temporary placeholder art. The other breeds in `DogBundle/PNGs/` aren't wired up yet.

## Status

This is an evolving hobby project, built incrementally. Personality now has a real hook into behavior (idle-activity selection - see Features) but it's a first pass; there's more surface area to wire up (see Roadmap).

## Roadmap / TODO

Not implemented yet, roughly in the order we're planning to tackle them:

- **Cosmetics** — something to actually spend currency on; the natural next step now that earning it works.
- **Tug rope** — mechanically different from Ball/Bone: hold one end (click and hold) and the pet comes to grab the other for a tug-of-war, rather than the usual throw/fetch. Saved for last since it needs its own interaction model instead of reusing the existing one.
- **A cat-chasing toy** (e.g. a little mouse that darts around erratically) — makes sense once a cat companion exists; no point building cat-specific behavior with nothing to use it yet.
- **Personality wired into more than idle behavior** — currently *which idle activity* the pet picks, and nothing else, is trait-weighted (the vocalization emotion thresholds are one more example of something still flat/global across pets). Other candidates: extraversion affecting how readily it approaches you, neuroticism affecting happiness decay rate, need thresholds, or the vocalization thresholds themselves (e.g. a more neurotic pet growls/whines more easily).
- **More species vocabulary** — a cat or robot companion would need their own `vocalizations.py` entry (meows/chirps/etc., not a bark); the lookup is already species-keyed, there's just only one species (dog) defined so far.
- **More dog breeds** — only the Corgi is wired into sprite rendering; `DogBundle/PNGs/` has 4 more unused.
- **A "Load" browser on the main menu** — right now you have to retype a saved pet's exact name there to resume it (the in-game pause menu's Load screen already lists saves properly).
- **Keyboard movement or jumping** for the pet.
