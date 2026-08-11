#!/usr/bin/python3
# npc.py

import os
import sys
import json
import pygame
import random as rand
import numpy as np

from npc_net import NPCAgent

BASE_DIR=os.path.dirname(__file__)
SAVE_DIR = os.path.join(BASE_DIR, "saves")

# Personality/need-knob fields persisted alongside the DQN weights.
PERSONALITY_FIELDS = [
    "open", "conscient", "extravers", "agreeable", "neuroticism",
    "hunger_threshold", "thirst_threshold", "boredom_threshold", "tiredness_threshold",
    "satiated_threshold", "interact_radius", "arrival_radius",
    "hunger_drain_rate", "thirst_drain_rate", "boredom_drain_rate", "tiredness_drain_rate",
    "happiness_decay_rate", "happiness_play_rate", "pet_happiness_boost", "pet_cooldown",
]

GRAVITY = 0.8
JUMP_FORCE = -16
GROUND_Y = 700  # 20px above the window's bottom edge, so a floor/grass strip shows beneath it
MOVE_SPEED = 100

HUNGER_RATE = 1       # hunger points gained per second, 0 (full) to 100 (starving)
THIRST_RATE = 1.5     # thirst points gained per second, 0 (full) to 100 (parched)
BOREDOM_RATE = 1.2    # boredom points gained per second, 0 (entertained) to 100 (bored)
# Tiredness accrues faster while the pet is actually moving or playing than
# while it's standing still, so idling around isn't as tiring as walking.
TIREDNESS_RATE_ACTIVE = 1.2
TIREDNESS_RATE_IDLE = 0.3

# Personality defaults: how urgently this pet seeks food/water/toys/rest, how
# close it needs to be to eat/drink/play, and how fast each need is satisfied.
# These live per-instance (see __init__) so different pets can be tuned later.
HUNGER_THRESHOLD = 75
THIRST_THRESHOLD = 50
BOREDOM_THRESHOLD = 55
TIREDNESS_THRESHOLD = 80
SATIATED_THRESHOLD = 5  # once seeking a need, keep eating/drinking/playing/resting until it drops below this
INTERACT_RADIUS = 60    # how close the pet needs to be to eat/drink/play
ARRIVAL_RADIUS = 20     # horizontal distance to target counted as "arrived" - stop walking
HUNGER_DRAIN_RATE = 50
THIRST_DRAIN_RATE = 50
BOREDOM_DRAIN_RATE = 50
TIREDNESS_DRAIN_RATE = 40  # recovery rate per second while resting (tiredness has no location - the pet just stops)

# Happiness isn't a "need" the pet seeks out on its own - it's a passive
# meter (100 = delighted, 0 = neglected) nudged by play and petting.
HAPPINESS_DECAY_RATE = 0.5  # happiness lost per second when left alone
HAPPINESS_PLAY_RATE = 15    # happiness gained per second while playing with the toy
PET_HAPPINESS_BOOST = 15    # happiness gained per click-to-pet
PET_COOLDOWN = 1.0          # seconds before another click-to-pet registers

STATE_SIZE = 4   # [npc.x, npc.y, target.x, target.y], all normalized to 0-1
ACTION_SIZE = 3  # 0: move left, 1: stay, 2: move right

class npc:
    def __init__(self, npc_name, screen, verbose=False):
        self.npc_name = npc_name
        self.screen = screen
        self.pos = pygame.Vector2(screen.get_width() / 2, screen.get_height() * 0.66)
        self.velocity_y = 0
        self.is_grounded = False
        self.move = 0
        self.verbose = verbose
        self.hunger = 0
        self.thirst = 0
        self.boredom = 0
        self.tiredness = 0
        self.happiness = 50  # neutral starting point; 100 = delighted, 0 = neglected
        self._pet_cooldown = 0  # seconds remaining before another click-to-pet registers

        #####################################################################
        #           The group enclosed below makes up personality           #
        #####################################################################

        # The prsonality as of right now will be based on 0 out of 10 0 being the least
        # and 10 being the most

        self.open = 0 # Creativity Curiosity and Love for new ideas
        self.conscient = 0 # Self control, organization, and focus to detail
        self.extravers = 0 # Energy, sociability, and boldness in groups.
        self.agreeable = 0 # Kindness Cooperation, and helpfulness
        self.neuroticism = 1 # tendency to experience negative emotions like anxiety or irritability

        #####################################################################

        # Personality knobs (per-instance so different pets can differ later).
        self.hunger_threshold = HUNGER_THRESHOLD
        self.thirst_threshold = THIRST_THRESHOLD
        self.boredom_threshold = BOREDOM_THRESHOLD
        self.tiredness_threshold = TIREDNESS_THRESHOLD
        self.satiated_threshold = SATIATED_THRESHOLD
        self.interact_radius = INTERACT_RADIUS
        self.arrival_radius = ARRIVAL_RADIUS
        self.hunger_drain_rate = HUNGER_DRAIN_RATE
        self.thirst_drain_rate = THIRST_DRAIN_RATE
        self.boredom_drain_rate = BOREDOM_DRAIN_RATE
        self.tiredness_drain_rate = TIREDNESS_DRAIN_RATE
        self.happiness_decay_rate = HAPPINESS_DECAY_RATE
        self.happiness_play_rate = HAPPINESS_PLAY_RATE
        self.pet_happiness_boost = PET_HAPPINESS_BOOST
        self.pet_cooldown = PET_COOLDOWN

        self.active_need = None  # "hunger"/"thirst"/"boredom"/"tiredness" while eating/drinking/playing/resting
        self.target_pos = self.pos
        self.agent = NPCAgent(STATE_SIZE, ACTION_SIZE)
        self.last_state = None
        self.last_action = None

        # Resume a previously saved pet (brain + personality) if one exists
        # for this name; otherwise roll a fresh personality.
        if not self.load():
            self.randomize_personality()

    def randomize_personality(self):
        # Not wired into behavior yet - reserved for future NPC/player
        # interaction logic (e.g. extraversion affecting how readily the pet
        # approaches others).
        self.open = rand.randint(3, 6)
        self.conscient = rand.randint(3, 5)
        self.extravers = rand.randint(4, 8)
        self.agreeable = rand.randint(4, 6)
        self.neuroticism = rand.randint(0, 2)

    def pet_interact(self):
        """Called when the player clicks directly on the pet. Returns True if
        it registered (subject to a cooldown so spam-clicking can't max out
        happiness instantly)."""
        if self._pet_cooldown > 0:
            return False
        self.happiness = min(100, self.happiness + self.pet_happiness_boost)
        self._pet_cooldown = self.pet_cooldown
        return True

    def _safe_name(self):
        """npc_name may come from free-text player input (naming a pet), so
        it must never be used raw in a filesystem path - strip it down to
        just alphanumerics/space/hyphen/underscore to rule out path
        traversal (e.g. a name like "../../etc") or invalid filenames."""
        cleaned = "".join(c for c in self.npc_name if c.isalnum() or c in " -_").strip()
        return cleaned or "pet"

    def _brain_path(self):
        return os.path.join(SAVE_DIR, f"{self._safe_name()}.pt")

    def _personality_path(self):
        return os.path.join(SAVE_DIR, f"{self._safe_name()}.json")

    def save(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        self.agent.save(self._brain_path())
        with open(self._personality_path(), "w") as f:
            json.dump({field: getattr(self, field) for field in PERSONALITY_FIELDS}, f, indent=2)

    def load(self):
        """Load a previously saved brain + personality for this npc_name.
        Returns True if a save was found and loaded, False otherwise."""
        try:
            self.agent.load(self._brain_path())
        except FileNotFoundError:
            return False

        try:
            with open(self._personality_path()) as f:
                personality = json.load(f)
            for field, value in personality.items():
                setattr(self, field, value)
        except FileNotFoundError:
            pass

        return True

    def get_state(self, target_pos):
        w, h = self.screen.get_width(), self.screen.get_height()
        return np.array([
            self.pos.x / w,
            self.pos.y / h,
            target_pos.x / w,
            target_pos.y / h,
        ], dtype=np.float32)

    def choose_target(self, mouse_pos, food_pos, water_pos, toy_pos):
        # need name -> (current value, seek threshold, target position)
        # Tiredness has no location to travel to - its "target" is just
        # wherever the pet already is, so pursuing it means standing still.
        needs = {
            "hunger": (self.hunger, self.hunger_threshold, food_pos),
            "thirst": (self.thirst, self.thirst_threshold, water_pos),
            "tiredness": (self.tiredness, self.tiredness_threshold, pygame.Vector2(self.pos)),
        }
        if toy_pos is not None:
            needs["boredom"] = (self.boredom, self.boredom_threshold, toy_pos)

        # Once a need is being actively addressed, keep pursuing it (even if
        # it dips back under its seek threshold) until it's well satisfied -
        # otherwise the pet would take one bite and wander off again.
        if self.active_need in needs:
            value, _, target = needs[self.active_need]
            if value > self.satiated_threshold:
                return target
            self.active_need = None

        urgent = [(name, value - threshold, target)
                  for name, (value, threshold, target) in needs.items()
                  if value >= threshold]
        if not urgent:
            return mouse_pos

        name, _, target = max(urgent, key=lambda n: n[1])
        self.active_need = name
        return target

    def update(self, dt, mouse_pos, food_pos, water_pos, toy_pos=None):
        self._pet_cooldown = max(0, self._pet_cooldown - dt)

        self.hunger = min(100, self.hunger + HUNGER_RATE * dt)
        self.thirst = min(100, self.thirst + THIRST_RATE * dt)
        self.boredom = min(100, self.boredom + BOREDOM_RATE * dt)
        self.happiness = max(0, self.happiness - self.happiness_decay_rate * dt)

        if self.pos.distance_to(food_pos) <= self.interact_radius:
            self.hunger = max(0, self.hunger - self.hunger_drain_rate * dt)
        if self.pos.distance_to(water_pos) <= self.interact_radius:
            self.thirst = max(0, self.thirst - self.thirst_drain_rate * dt)

        playing = toy_pos is not None and self.pos.distance_to(toy_pos) <= self.interact_radius
        if playing:
            self.boredom = max(0, self.boredom - self.boredom_drain_rate * dt)
            self.happiness = min(100, self.happiness + self.happiness_play_rate * dt)
        if self.active_need == "tiredness":
            self.tiredness = max(0, self.tiredness - self.tiredness_drain_rate * dt)

        target_pos = self.target_pos = self.choose_target(mouse_pos, food_pos, water_pos, toy_pos)

        self.velocity_y += GRAVITY
        self.pos.y += self.velocity_y

        if self.pos.y + 40 >= GROUND_Y:
            self.pos.y = GROUND_Y - 40
            self.velocity_y = 0
            self.is_grounded = True
        else:
            self.is_grounded = False

        state = self.get_state(target_pos)
        action = self.agent.act(state)

        # Once horizontally close enough, stop walking instead of jittering
        # around the target - only resume once the target moves far enough
        # away again (recomputed fresh every frame, so no separate "target
        # changed" tracking is needed).
        arrived = abs(self.pos.x - target_pos.x) <= self.arrival_radius
        self.move = 0 if arrived else (action - 1)  # -1: left, 0: stay, 1: right

        # Measure distance to this frame's (frozen) target before and after
        # the pet's own move, so reward only reflects the pet closing the
        # gap itself, not the target moving toward/away from the pet.
        prev_dist = self.pos.distance_to(target_pos)
        self.pos.x += self.move * MOVE_SPEED * dt
        new_dist = self.pos.distance_to(target_pos)
        reward = (prev_dist - new_dist) / 10

        if self.last_state is not None:
            self.agent.remember(self.last_state, self.last_action, reward, state, False)
            self.agent.replay()

        self.last_state = state
        self.last_action = action

        # Moving around or actively playing wears the pet out faster than
        # standing still.
        is_active = self.move != 0 or playing
        tiredness_rate = TIREDNESS_RATE_ACTIVE if is_active else TIREDNESS_RATE_IDLE
        self.tiredness = min(100, self.tiredness + tiredness_rate * dt)

        if self.verbose:
            print(f"action={action} move={self.move} reward={reward:.3f} epsilon={self.agent.epsilon:.3f} "
                  f"hunger={self.hunger:.1f} thirst={self.thirst:.1f} boredom={self.boredom:.1f} "
                  f"tiredness={self.tiredness:.1f} happiness={self.happiness:.1f}")

