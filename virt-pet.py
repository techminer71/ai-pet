# Example file showing a circle moving on screen
import random

import pygame

from npc import npc, GROUND_Y
import items
from items import item

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
running = True
dt = 0

temp_cir_rad = 40
pet = npc("pet", screen, verbose=True)

food = item("food", items.FOOD, screen, pygame.Vector2(100, GROUND_Y))
water = item("water", items.WATER, screen, pygame.Vector2(1180, GROUND_Y))
toy = item("toy", items.TOY, screen, pygame.Vector2(640, GROUND_Y))
toy.active = False  # not on the field until the toy button is clicked

BAR_WIDTH, BAR_HEIGHT, BAR_GAP = 200, 18, 8

def draw_stat_bar(x, y, value, color):
    pygame.draw.rect(screen, "gray20", (x, y, BAR_WIDTH, BAR_HEIGHT))
    fill_width = int(BAR_WIDTH * (value / 100))
    pygame.draw.rect(screen, color, (x, y, fill_width, BAR_HEIGHT))
    pygame.draw.rect(screen, "black", (x, y, BAR_WIDTH, BAR_HEIGHT), 2)

TOY_BUTTON_RECT = pygame.Rect(screen.get_width() - 120, 20, 100, 40)

def draw_toy_button():
    pygame.draw.rect(screen, items.COLORS[items.TOY], TOY_BUTTON_RECT, border_radius=6)
    pygame.draw.rect(screen, "black", TOY_BUTTON_RECT, 2, border_radius=6)
    label = font.render("Toy", True, "black")
    screen.blit(label, label.get_rect(center=TOY_BUTTON_RECT.center))

while running:
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if TOY_BUTTON_RECT.collidepoint(event.pos):
                # Drop (or re-throw) the toy at a random spot on the ground.
                toy.active = True
                toy.pos = pygame.Vector2(random.randint(150, 1130), GROUND_Y)

    # fill the screen with a color to wipe away anything from last frame
    screen.fill("skyblue1")

    food.draw()
    water.draw()
    if toy.active:
        toy.draw()

    # Mouse position stands in for the future "player" target.
    mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
    toy_pos = toy.pos if toy.active else None
    pet.update(dt, mouse_pos, food.pos, water.pos, toy_pos)

    # Marker shows whichever target the pet actually chose this frame
    # (mouse, food, water, or toy), so need-driven behavior is visible.
    pygame.draw.circle(screen, "yellow", pet.target_pos, 8)
    pygame.draw.circle(screen, "red", pet.pos, temp_cir_rad)

    draw_stat_bar(20, 20, pet.hunger, items.COLORS[items.FOOD])
    draw_stat_bar(20, 20 + BAR_HEIGHT + BAR_GAP, pet.thirst, items.COLORS[items.WATER])
    draw_stat_bar(20, 20 + 2 * (BAR_HEIGHT + BAR_GAP), pet.boredom, items.COLORS[items.TOY])

    draw_toy_button()

    # flip() the display to put your work on screen
    pygame.display.flip()

    # limits FPS to 60
    # dt is delta time in seconds since last frame, used for framerate-
    # independent physics.
    dt = clock.tick(60) / 1000

pygame.quit()
