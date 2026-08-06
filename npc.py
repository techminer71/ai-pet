#!/usr/bin/python3
# npc.py

import os
import sys
import pygame
import random as rand
import numpy as np

from npc_net import NPCAgent

BASE_DIR=os.path.dirname(__file__)

GRAVITY = 0.8
JUMP_FORCE = -16
GROUND_Y = 720
MOVE_SPEED = 100

HUNGER_RATE = 1     # hunger points gained per second, 0 (full) to 100 (starving)
THIRST_RATE = 1.5   # thirst points gained per second, 0 (full) to 100 (parched)
BOREDOM_RATE = 1.2  # boredom points gained per second, 0 (entertained) to 100 (bored)

# Personality defaults: how urgently this pet seeks food/water/toys, how close
# it needs to be to eat/drink/play, and how fast each need is satisfied. These
# live per-instance (see __init__) so different pets can be tuned differently.
HUNGER_THRESHOLD = 75
THIRST_THRESHOLD = 50
BOREDOM_THRESHOLD = 55
SATIATED_THRESHOLD = 5  # once seeking a need, keep eating/drinking/playing until it drops below this
INTERACT_RADIUS = 60    # how close the pet needs to be to eat/drink/play
HUNGER_DRAIN_RATE = 50
THIRST_DRAIN_RATE = 50
BOREDOM_DRAIN_RATE = 50

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

        self.randomize_personality()

        #####################################################################

        # Personality knobs (per-instance so different pets can differ later).
        self.hunger_threshold = HUNGER_THRESHOLD
        self.thirst_threshold = THIRST_THRESHOLD
        self.boredom_threshold = BOREDOM_THRESHOLD
        self.satiated_threshold = SATIATED_THRESHOLD
        self.interact_radius = INTERACT_RADIUS
        self.hunger_drain_rate = HUNGER_DRAIN_RATE
        self.thirst_drain_rate = THIRST_DRAIN_RATE
        self.boredom_drain_rate = BOREDOM_DRAIN_RATE

        self.active_need = None  # "hunger"/"thirst"/"boredom" while eating/drinking/playing
        self.target_pos = self.pos
        self.agent = NPCAgent(STATE_SIZE, ACTION_SIZE)
        self.last_state = None
        self.last_action = None

    def randomize_personality(self):
        # Not wired into behavior yet - reserved for future NPC/player
        # interaction logic (e.g. extraversion affecting how readily the pet
        # approaches others).
        self.open = rand.randint(3, 6)
        self.conscient = rand.randint(3, 5)
        self.extravers = rand.randint(4, 8)
        self.agreeable = rand.randint(4, 6)
        self.neuroticism = rand.randint(0, 2)

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
        needs = {
            "hunger": (self.hunger, self.hunger_threshold, food_pos),
            "thirst": (self.thirst, self.thirst_threshold, water_pos),
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
        self.hunger = min(100, self.hunger + HUNGER_RATE * dt)
        self.thirst = min(100, self.thirst + THIRST_RATE * dt)
        self.boredom = min(100, self.boredom + BOREDOM_RATE * dt)

        if self.pos.distance_to(food_pos) <= self.interact_radius:
            self.hunger = max(0, self.hunger - self.hunger_drain_rate * dt)
        if self.pos.distance_to(water_pos) <= self.interact_radius:
            self.thirst = max(0, self.thirst - self.thirst_drain_rate * dt)
        if toy_pos is not None and self.pos.distance_to(toy_pos) <= self.interact_radius:
            self.boredom = max(0, self.boredom - self.boredom_drain_rate * dt)

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
        self.move = action - 1  # -1: left, 0: stay, 1: right

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

        if self.verbose:
            print(f"action={action} reward={reward:.3f} epsilon={self.agent.epsilon:.3f} "
                  f"hunger={self.hunger:.1f} thirst={self.thirst:.1f} boredom={self.boredom:.1f}")

