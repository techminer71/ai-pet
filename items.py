#!/usr/bin/python3
# items.py

import random

import pygame

FOOD = "food"
WATER = "water"
TOY = "toy"

COLORS = {
    FOOD: "saddlebrown",
    WATER: "dodgerblue",
    TOY: "orange",
}

TOY_RADIUS = 15
TOY_GRAVITY = 1500     # px/s^2
BOUNCE_DAMPING = 0.5   # fraction of vertical speed kept after each ground bounce
WALL_DAMPING = 0.8     # fraction of horizontal speed kept after each wall/ground bounce
MIN_BOUNCE_SPEED = 60  # below this vertical speed, just settle instead of bouncing forever


class item:
    def __init__(self, item_name, item_type, screen, pos, verbose=False):
        self.name = item_name
        self.item_type = item_type  # items.FOOD, items.WATER, or items.TOY
        self.screen = screen
        self.pos = pygame.Vector2(pos)  # ground position (midbottom of the item's shape)
        self.verbose = verbose

        # Throw physics (only meaningful for the toy - food/water never move).
        self.velocity = pygame.Vector2(0, 0)
        self.bounces_remaining = 0
        self.on_ground = True

    def throw(self, velocity, bounces=None):
        """Launch the item with an initial velocity. It falls under gravity,
        bounces off the ground once or twice (losing energy each time), and
        reflects off the screen edges so it stays in view."""
        self.velocity = pygame.Vector2(velocity)
        self.bounces_remaining = bounces if bounces is not None else random.randint(1, 2)
        self.on_ground = False

    def physics_update(self, dt, ground_y, screen_width):
        if self.on_ground:
            return

        self.velocity.y += TOY_GRAVITY * dt
        self.pos += self.velocity * dt

        if self.pos.x <= TOY_RADIUS:
            self.pos.x = TOY_RADIUS
            self.velocity.x *= -1
        elif self.pos.x >= screen_width - TOY_RADIUS:
            self.pos.x = screen_width - TOY_RADIUS
            self.velocity.x *= -1

        if self.pos.y <= TOY_RADIUS:
            self.pos.y = TOY_RADIUS
            self.velocity.y *= -1

        if self.pos.y >= ground_y:
            self.pos.y = ground_y
            if self.bounces_remaining > 0 and abs(self.velocity.y) > MIN_BOUNCE_SPEED:
                self.velocity.y *= -BOUNCE_DAMPING
                self.velocity.x *= WALL_DAMPING
                self.bounces_remaining -= 1
            else:
                self.velocity = pygame.Vector2(0, 0)
                self.on_ground = True

    def draw(self):
        color = COLORS[self.item_type]

        if self.item_type == FOOD:
            rect = pygame.Rect(0, 0, 50, 35)
            rect.midbottom = self.pos
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
        elif self.item_type == WATER:
            rect = pygame.Rect(0, 0, 100, 30)
            rect.midbottom = self.pos
            pygame.draw.ellipse(self.screen, color, rect)
        elif self.item_type == TOY:
            center = (self.pos.x, self.pos.y - TOY_RADIUS)
            pygame.draw.circle(self.screen, color, center, TOY_RADIUS)
