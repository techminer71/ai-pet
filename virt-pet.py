# Example file showing a circle moving on screen
import os
import random

import pygame

from npc import npc, GROUND_Y, SAVE_DIR
import items
from items import item

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
title_font = pygame.font.SysFont(None, 56)
running = True
dt = 0

temp_cir_rad = 40
MAX_NAME_LEN = 16

AUTOSAVE_INTERVAL = 30  # seconds
autosave_timer = 0

food = item("food", items.FOOD, screen, pygame.Vector2(100, GROUND_Y))
water = item("water", items.WATER, screen, pygame.Vector2(1180, GROUND_Y))
toy = item("toy", items.TOY, screen, pygame.Vector2(640, GROUND_Y))
toy.active = False  # not on the field until the toy button is clicked

# --- Game state machine ---------------------------------------------------
# MENU: name a pet and start. PLAYING: the game itself. PAUSED: pause overlay
# (resume/save/load/back to menu). LOAD: pick a different saved pet to switch to.
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_LOAD = "load"
state = STATE_MENU

pet = None
name_input = ""


def safe_save():
    if pet is not None:
        try:
            pet.save()
        except Exception as e:
            print(f"save failed: {e}")


def start_pet(name):
    global pet
    pet = npc(name.strip() or "pet", screen, verbose=True)
    toy.active = False


def list_saved_pets():
    if not os.path.isdir(SAVE_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(SAVE_DIR) if f.endswith(".json"))


# --- Shared drawing helpers -------------------------------------------------

BAR_WIDTH, BAR_HEIGHT, BAR_GAP = 200, 18, 8

def draw_stat_bar(x, y, value, color):
    pygame.draw.rect(screen, "gray20", (x, y, BAR_WIDTH, BAR_HEIGHT))
    fill_width = int(BAR_WIDTH * (value / 100))
    pygame.draw.rect(screen, color, (x, y, fill_width, BAR_HEIGHT))
    pygame.draw.rect(screen, "black", (x, y, BAR_WIDTH, BAR_HEIGHT), 2)

GRASS_COLOR = "yellowgreen"
GRASS_EDGE_COLOR = "darkgreen"
GRASS_EDGE_HEIGHT = 4

def draw_ground():
    ground_rect = pygame.Rect(0, GROUND_Y, screen.get_width(), screen.get_height() - GROUND_Y)
    pygame.draw.rect(screen, GRASS_COLOR, ground_rect)
    pygame.draw.rect(screen, GRASS_EDGE_COLOR, (0, GROUND_Y, screen.get_width(), GRASS_EDGE_HEIGHT))

TOY_BUTTON_RECT = pygame.Rect(screen.get_width() - 120, 20, 100, 40)

def draw_toy_button():
    pygame.draw.rect(screen, items.COLORS[items.TOY], TOY_BUTTON_RECT, border_radius=6)
    pygame.draw.rect(screen, "black", TOY_BUTTON_RECT, 2, border_radius=6)
    label = font.render("Toy", True, "black")
    screen.blit(label, label.get_rect(center=TOY_BUTTON_RECT.center))

def draw_button(rect, label, color="white"):
    pygame.draw.rect(screen, color, rect, border_radius=6)
    pygame.draw.rect(screen, "black", rect, 2, border_radius=6)
    text = font.render(label, True, "black")
    screen.blit(text, text.get_rect(center=rect.center))

def draw_scene():
    """Draws the game world (ground/items/pet/bars) without advancing
    anything - used both while playing and, frozen, behind the pause menu."""
    screen.fill("skyblue1")
    draw_ground()
    food.draw()
    water.draw()
    if toy.active:
        toy.draw()
    pygame.draw.circle(screen, "yellow", pet.target_pos, 8)
    pygame.draw.circle(screen, "red", pet.pos, temp_cir_rad)
    draw_stat_bar(20, 20, pet.hunger, items.COLORS[items.FOOD])
    draw_stat_bar(20, 20 + BAR_HEIGHT + BAR_GAP, pet.thirst, items.COLORS[items.WATER])
    draw_stat_bar(20, 20 + 2 * (BAR_HEIGHT + BAR_GAP), pet.boredom, items.COLORS[items.TOY])
    draw_stat_bar(20, 20 + 3 * (BAR_HEIGHT + BAR_GAP), pet.tiredness, "mediumpurple")
    draw_stat_bar(20, 20 + 4 * (BAR_HEIGHT + BAR_GAP), pet.happiness, "hotpink")
    draw_toy_button()

# --- Menu screen -------------------------------------------------------------

NAME_BOX_RECT = pygame.Rect(440, 300, 400, 44)
START_BUTTON_RECT = pygame.Rect(540, 370, 200, 50)
QUIT_BUTTON_RECT = pygame.Rect(540, 440, 200, 50)

def draw_menu():
    screen.fill("skyblue1")
    title = title_font.render("AI Pet", True, "black")
    screen.blit(title, title.get_rect(center=(screen.get_width() // 2, 180)))

    pygame.draw.rect(screen, "white", NAME_BOX_RECT, border_radius=6)
    pygame.draw.rect(screen, "black", NAME_BOX_RECT, 2, border_radius=6)
    if name_input:
        text_surf = font.render(name_input, True, "black")
    else:
        text_surf = font.render("Enter pet name...", True, "gray50")
    screen.blit(text_surf, (NAME_BOX_RECT.x + 10, NAME_BOX_RECT.y + 13))

    draw_button(START_BUTTON_RECT, "Start")
    draw_button(QUIT_BUTTON_RECT, "Quit")

# --- Pause menu ---------------------------------------------------------------

RESUME_BUTTON_RECT = pygame.Rect(540, 250, 200, 50)
SAVE_BUTTON_RECT = pygame.Rect(540, 320, 200, 50)
LOAD_BUTTON_RECT = pygame.Rect(540, 390, 200, 50)
MAIN_MENU_BUTTON_RECT = pygame.Rect(540, 460, 200, 50)

def draw_pause_menu():
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    title = title_font.render("Paused", True, "white")
    screen.blit(title, title.get_rect(center=(screen.get_width() // 2, 170)))

    draw_button(RESUME_BUTTON_RECT, "Resume")
    draw_button(SAVE_BUTTON_RECT, "Save")
    draw_button(LOAD_BUTTON_RECT, "Load")
    draw_button(MAIN_MENU_BUTTON_RECT, "Back to Main Menu")

# --- Load-a-different-pet screen ----------------------------------------------

LOAD_BACK_BUTTON_RECT = pygame.Rect(40, 40, 120, 44)

def load_menu_entries():
    names = list_saved_pets()
    entries = []
    y = 180
    for saved_name in names:
        entries.append((pygame.Rect(490, y, 300, 44), saved_name))
        y += 56
    return entries

def draw_load_menu(entries):
    screen.fill("skyblue1")
    title = title_font.render("Load Pet", True, "black")
    screen.blit(title, title.get_rect(center=(screen.get_width() // 2, 100)))

    if not entries:
        msg = font.render("No saved pets yet.", True, "black")
        screen.blit(msg, msg.get_rect(center=(screen.get_width() // 2, 180)))
    for rect, saved_name in entries:
        draw_button(rect, saved_name)

    draw_button(LOAD_BACK_BUTTON_RECT, "Back")

# --- Main loop -----------------------------------------------------------------

while running:
    if state == STATE_LOAD:
        current_load_entries = load_menu_entries()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            safe_save()
            running = False
            continue

        if state == STATE_MENU:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RETURN:
                    start_pet(name_input)
                    state = STATE_PLAYING
                elif event.key == pygame.K_BACKSPACE:
                    name_input = name_input[:-1]
                elif event.unicode and (event.unicode.isalnum() or event.unicode in " -_"):
                    if len(name_input) < MAX_NAME_LEN:
                        name_input += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if START_BUTTON_RECT.collidepoint(event.pos):
                    start_pet(name_input)
                    state = STATE_PLAYING
                elif QUIT_BUTTON_RECT.collidepoint(event.pos):
                    running = False

        elif state == STATE_PLAYING:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = STATE_PAUSED
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if TOY_BUTTON_RECT.collidepoint(event.pos):
                    # Throw the toy from wherever it currently sits, in a
                    # random direction; it falls under gravity and bounces.
                    toy.active = True
                    throw_velocity = pygame.Vector2(random.uniform(-450, 450), random.uniform(-650, -450))
                    toy.throw(throw_velocity)
                elif pygame.Vector2(event.pos).distance_to(pet.pos) <= temp_cir_rad:
                    pet.pet_interact()

        elif state == STATE_PAUSED:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = STATE_PLAYING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if RESUME_BUTTON_RECT.collidepoint(event.pos):
                    state = STATE_PLAYING
                elif SAVE_BUTTON_RECT.collidepoint(event.pos):
                    safe_save()
                elif LOAD_BUTTON_RECT.collidepoint(event.pos):
                    state = STATE_LOAD
                elif MAIN_MENU_BUTTON_RECT.collidepoint(event.pos):
                    safe_save()
                    pet = None
                    name_input = ""
                    toy.active = False
                    state = STATE_MENU

        elif state == STATE_LOAD:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = STATE_PAUSED
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if LOAD_BACK_BUTTON_RECT.collidepoint(event.pos):
                    state = STATE_PAUSED
                else:
                    for rect, saved_name in current_load_entries:
                        if rect.collidepoint(event.pos):
                            safe_save()  # keep the outgoing pet's progress
                            start_pet(saved_name)
                            state = STATE_PLAYING
                            break

    if state == STATE_MENU:
        draw_menu()

    elif state == STATE_PLAYING:
        # Mouse position stands in for the future "player" target.
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        toy_pos = toy.pos if toy.active else None
        if toy.active:
            toy.physics_update(dt, GROUND_Y, screen.get_width())
        pet.update(dt, mouse_pos, food.pos, water.pos, toy_pos)
        draw_scene()

        autosave_timer += dt
        if autosave_timer >= AUTOSAVE_INTERVAL:
            safe_save()
            autosave_timer = 0

    elif state == STATE_PAUSED:
        # World is frozen: draw the last state without updating it.
        draw_scene()
        draw_pause_menu()

    elif state == STATE_LOAD:
        draw_load_menu(current_load_entries)

    # flip() the display to put your work on screen
    pygame.display.flip()

    # limits FPS to 60
    # dt is delta time in seconds since last frame, used for framerate-
    # independent physics.
    dt = clock.tick(60) / 1000

safe_save()
pygame.quit()
