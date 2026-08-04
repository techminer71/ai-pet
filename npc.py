#!/usr/bin/python3
# npc.py

import os
import sys
import pygame
import random as rand

BASE_DIR=os.path.dirname(__file__)

GRAVITY = 0.8
JUMP_FORCE = -16
GROUND_Y = 720

class npc:
    def __init__(self, npc_name, screen, verbose=False):
        self.npc_name = npc_name
        self.pos = pygame.Vector2(screen.get_width() / 2, screen.get_height() * 0.66)
        self.velocity_y = 0
        self.is_grounded = False
        self.move = 0

    def update(self, dt): 
        self.move = move = (rand.random() * 2) - 1
        self.velocity_y += GRAVITY
        self.pos.y += self.velocity_y

        if self.pos.y + 40 >= GROUND_Y:
            self.pos.y = GROUND_Y - 40
            self.velocity_y = 0
            self.is_grounded = True

        if self.move >= 0.25:
            self.pos.x += 100 * dt
        if self.move <= -0.25:
            self.pos.x -= 100 * dt

