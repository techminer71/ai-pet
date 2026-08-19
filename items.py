#!/usr/bin/python3
# items.py

import random

import pygame

FOOD = "food"
WATER = "water"
TOY = "toy"
BED = "bed"
TOYBOX = "toybox"

COLORS = {
    FOOD: "saddlebrown",
    WATER: "dodgerblue",
    TOY: "orange",
    BED: "peru",
    TOYBOX: "sienna",
}

# Different toy kinds share all the same throw/fetch/self-play mechanics
# (see npc.py) - only their look differs, via `item.kind` and this table.
TOY_KIND_COLORS = {
    "ball": "orange",
    "bone": "oldlace",
}

TOY_RADIUS = 15
TOY_GRAVITY = 1500     # px/s^2
BOUNCE_DAMPING = 0.5   # fraction of vertical speed kept after each ground bounce
WALL_DAMPING = 0.8     # fraction of horizontal speed kept after each wall/ground bounce
MIN_BOUNCE_SPEED = 60  # below this vertical speed, just settle instead of bouncing forever

# Player-thrown balls are fully deterministic from click position (not
# randomized like the pet's own self-play throw) - the point is precise
# control: which half of the ball you click sets the direction, and how
# close to the edge sets the power.
THROW_MIN_SPEED = 250   # weakest throw - click near the ball's center
THROW_MAX_SPEED = 700   # strongest throw - click right at the edge
THROW_VY_RATIO = 1.15   # vertical launch speed, relative to horizontal speed, for a consistent arc


class item:
    def __init__(self, item_name, item_type, screen, pos, kind=None, verbose=False):
        self.name = item_name
        self.item_type = item_type  # items.FOOD, items.WATER, or items.TOY
        self.screen = screen
        self.pos = pygame.Vector2(pos)  # ground position (midbottom of the item's shape)
        self.kind = kind  # only meaningful for TOY - e.g. "ball"/"bone", see TOY_KIND_COLORS
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

    def throw_toward(self, click_pos):
        """Throw the toy based on where on it the player clicked: the right
        half throws left and vice versa, with power scaling from how close
        to the edge the click landed (center = weakest, edge = strongest).
        Deterministic by design - the point is giving the player control,
        unlike the pet's own randomized self-play throw."""
        center = pygame.Vector2(self.pos.x, self.pos.y - TOY_RADIUS)
        offset = pygame.Vector2(click_pos) - center
        closeness_to_edge = min(offset.length() / TOY_RADIUS, 1.0)
        speed = THROW_MIN_SPEED + (THROW_MAX_SPEED - THROW_MIN_SPEED) * closeness_to_edge
        direction = -1 if offset.x >= 0 else 1  # clicked the right half -> throw left
        self.throw(pygame.Vector2(direction * speed, -speed * THROW_VY_RATIO))

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

    def get_rect(self):
        """Bounding rect, matching the shape drawn in draw() - used for
        click-to-feed/water hit-testing (FOOD/WATER) and for drawing (also
        BED, which isn't clickable)."""
        if self.item_type == FOOD:
            rect = pygame.Rect(0, 0, 50, 35)
        elif self.item_type == WATER:
            rect = pygame.Rect(0, 0, 100, 30)
        elif self.item_type == BED:
            rect = pygame.Rect(0, 0, 90, 24)
        else:  # TOYBOX
            rect = pygame.Rect(0, 0, 60, 40)
        rect.midbottom = self.pos
        return rect

    def contains_point(self, pos):
        """Precise click hit-test matching the shape drawn in draw() - used
        for click-to-feed/water/throw. The toy is round, so get_rect()'s
        bounding box would catch clicks in its corners that miss the circle."""
        if self.item_type == TOY:
            center = pygame.Vector2(self.pos.x, self.pos.y - TOY_RADIUS)
            return center.distance_to(pos) <= TOY_RADIUS
        return self.get_rect().collidepoint(pos)

    def place(self, pos):
        """Reset to a resting position with no throw in progress - used when
        the player brings a toy out from the toy menu."""
        self.pos = pygame.Vector2(pos)
        self.velocity = pygame.Vector2(0, 0)
        self.bounces_remaining = 0
        self.on_ground = True

    def draw(self):
        color = COLORS[self.item_type]

        if self.item_type == FOOD:
            pygame.draw.rect(self.screen, color, self.get_rect(), border_radius=4)
        elif self.item_type == WATER:
            pygame.draw.ellipse(self.screen, color, self.get_rect())
        elif self.item_type == TOY:
            center = (self.pos.x, self.pos.y - TOY_RADIUS)
            toy_color = TOY_KIND_COLORS.get(self.kind, color)
            if self.kind == "bone":
                self._draw_bone(center, toy_color)
            else:  # "ball" (also the fallback for an unset/unknown kind)
                pygame.draw.circle(self.screen, toy_color, center, TOY_RADIUS)
        elif self.item_type == BED:
            pygame.draw.rect(self.screen, color, self.get_rect(), border_radius=10)
        elif self.item_type == TOYBOX:
            rect = self.get_rect()
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, "black", rect, 2, border_radius=4)
            pygame.draw.line(self.screen, "black", rect.midtop, rect.midbottom, 2)  # split lid

    def _draw_bone(self, center, color):
        """Classic dog-bone silhouette: a shaft with a pair of round knobs
        at each end. Hit-testing/throw physics stay TOY_RADIUS-circle-based
        regardless of kind (see contains_point/throw_toward) - only the
        look differs."""
        cx, cy = center
        shaft_w, shaft_h = TOY_RADIUS * 2.2, TOY_RADIUS * 0.7
        knob_radius = TOY_RADIUS * 0.55
        shaft_rect = pygame.Rect(0, 0, shaft_w, shaft_h)
        shaft_rect.center = (cx, cy)
        pygame.draw.rect(self.screen, color, shaft_rect, border_radius=int(shaft_h / 2))
        for dx in (-shaft_w / 2, shaft_w / 2):
            for dy in (-shaft_h / 2, shaft_h / 2):
                pygame.draw.circle(self.screen, color, (cx + dx, cy + dy), knob_radius)
