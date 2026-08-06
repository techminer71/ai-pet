#!/usr/bin/python3
# items.py

import pygame

FOOD = "food"
WATER = "water"
TOY = "toy"

COLORS = {
    FOOD: "saddlebrown",
    WATER: "dodgerblue",
    TOY: "orange",
}


class item:
    def __init__(self, item_name, item_type, screen, pos, verbose=False):
        self.name = item_name
        self.item_type = item_type  # items.FOOD, items.WATER, or items.TOY
        self.screen = screen
        self.pos = pos  # ground position (midbottom of the item's shape)
        self.verbose = verbose

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
            radius = 15
            center = (self.pos.x, self.pos.y - radius)
            pygame.draw.circle(self.screen, color, center, radius)
