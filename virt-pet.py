# Example file showing a circle moving on screen
import os
import random

import pygame

from npc import npc, GROUND_Y, SAVE_DIR
import items
from items import item
from wallet import Wallet

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
title_font = pygame.font.SysFont(None, 56)
running = True
dt = 0

MAX_NAME_LEN = 16
DEFAULT_PET_NAME = "Steva"

AUTOSAVE_INTERVAL = 30  # seconds
autosave_timer = 0

food = item("food", items.FOOD, screen, pygame.Vector2(100, GROUND_Y))
water = item("water", items.WATER, screen, pygame.Vector2(1180, GROUND_Y))
bed = item("bed", items.BED, screen, pygame.Vector2(950, GROUND_Y))
toybox = item("toybox", items.TOYBOX, screen, pygame.Vector2(450, GROUND_Y))
toy = item("toy", items.TOY, screen, pygame.Vector2(640, GROUND_Y), kind="ball")
toy.active = False  # not on the field until a toy is picked (or the pet grabs one) from the toybox
TOY_DEFAULT_POS = pygame.Vector2(toybox.pos.x + 50, GROUND_Y)  # where a freshly-brought-out toy rests

wallet = Wallet()  # the player's currency - not tied to any one pet, see wallet.py

# --- Game state machine ---------------------------------------------------
# MENU: name a pet and start. PLAYING: the game itself. PAUSED: pause overlay
# (resume/save/load/back to menu). LOAD: pick a different saved pet to switch to.
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_LOAD = "load"
state = STATE_MENU

pet = None
name_input = DEFAULT_PET_NAME
context_menu_pos = None  # None = closed; a pos = open there (right-click, in-game only)
toy_menu_open = False  # toy-selection dropdown, opened by clicking the toybox
toy_menu_anchor = None  # where to draw it - set fresh each time it opens (toybox doesn't move, but keeps this consistent with context_menu_pos)


def safe_save():
    if pet is not None:
        try:
            pet.save()
        except Exception as e:
            print(f"save failed: {e}")


def start_pet(name):
    global pet
    pet = npc(name.strip() or DEFAULT_PET_NAME, screen, verbose=True)
    toy.active = False


def list_saved_pets():
    if not os.path.isdir(SAVE_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(SAVE_DIR) if f.endswith(".json"))


# --- Shared drawing helpers -------------------------------------------------

BAR_WIDTH, BAR_HEIGHT, BAR_GAP = 200, 18, 8

def draw_stat_bar(x, y, value, color, label):
    pygame.draw.rect(screen, "gray20", (x, y, BAR_WIDTH, BAR_HEIGHT))
    fill_width = int(BAR_WIDTH * (value / 100))
    pygame.draw.rect(screen, color, (x, y, fill_width, BAR_HEIGHT))
    pygame.draw.rect(screen, "black", (x, y, BAR_WIDTH, BAR_HEIGHT), 2)
    text = font.render(label, True, "black")
    screen.blit(text, (x + BAR_WIDTH + 10, y + (BAR_HEIGHT - text.get_height()) // 2))

GRASS_COLOR = "yellowgreen"
GRASS_EDGE_COLOR = "darkgreen"
GRASS_EDGE_HEIGHT = 4

def draw_ground():
    ground_rect = pygame.Rect(0, GROUND_Y, screen.get_width(), screen.get_height() - GROUND_Y)
    pygame.draw.rect(screen, GRASS_COLOR, ground_rect)
    pygame.draw.rect(screen, GRASS_EDGE_COLOR, (0, GROUND_Y, screen.get_width(), GRASS_EDGE_HEIGHT))

def draw_button(rect, label, color="white"):
    pygame.draw.rect(screen, color, rect, border_radius=6)
    pygame.draw.rect(screen, "black", rect, 2, border_radius=6)
    text = font.render(label, True, "black")
    screen.blit(text, text.get_rect(center=rect.center))

def draw_wallet():
    """Coin counter, top-right - roughly where the old Toys button used to
    sit before it became the toybox. Not tied to any single pet - see
    wallet.py."""
    cx, cy = screen.get_width() - 130, 38
    pygame.draw.circle(screen, "gold", (cx, cy), 11)
    pygame.draw.circle(screen, "black", (cx, cy), 11, 2)
    text = font.render(str(wallet.currency), True, "black")
    screen.blit(text, (cx + 18, cy - text.get_height() // 2))

def draw_scene():
    """Draws the game world (ground/items/pet/bars) without advancing
    anything - used both while playing and, frozen, behind the pause menu."""
    screen.fill("skyblue1")
    draw_ground()
    food.draw()
    water.draw()
    bed.draw()
    toybox.draw()
    if toy.active:
        toy.draw()
    if pet.active_need is not None or pet.called:
        pygame.draw.circle(screen, "yellow", pet.target_pos, 8)
    pet.draw()
    draw_stat_bar(20, 20, pet.hunger, items.COLORS[items.FOOD], "Hunger")
    draw_stat_bar(20, 20 + BAR_HEIGHT + BAR_GAP, pet.thirst, items.COLORS[items.WATER], "Thirst")
    draw_stat_bar(20, 20 + 2 * (BAR_HEIGHT + BAR_GAP), pet.boredom, items.COLORS[items.TOY], "Boredom")
    draw_stat_bar(20, 20 + 3 * (BAR_HEIGHT + BAR_GAP), pet.tiredness, "mediumpurple", "Tiredness")
    draw_stat_bar(20, 20 + 4 * (BAR_HEIGHT + BAR_GAP), pet.happiness, "hotpink", "Happiness")
    draw_wallet()

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

# --- Right-click context menu (in-game) ---------------------------------------

CONTEXT_MENU_OPTION_SIZE = (120, 36)
CONTEXT_MENU_OPTIONS = ["Call", "Pet", "Fetch"]  # more may join later (e.g. per-item actions)

def context_menu_entries(anchor_pos):
    """Rects for each option, clamped so the menu stays on-screen. Computed
    fresh on each access rather than cached (see load_menu_entries - a stale
    per-frame cache here bit us once already for the load screen)."""
    w, h = CONTEXT_MENU_OPTION_SIZE
    x = min(anchor_pos[0], screen.get_width() - w)
    y = min(anchor_pos[1], screen.get_height() - h * len(CONTEXT_MENU_OPTIONS))
    entries = []
    for i, label in enumerate(CONTEXT_MENU_OPTIONS):
        entries.append((pygame.Rect(x, y + i * h, w, h), label))
    return entries

def draw_context_menu(anchor_pos):
    for rect, label in context_menu_entries(anchor_pos):
        draw_button(rect, label)

# --- Toy menu (in-game) --------------------------------------------------------
# Opened by clicking the toybox. Selecting a toy that's already out again
# toggles it off (see the click handler below) rather than needing a
# separate remove control.

TOY_MENU_OPTIONS = ["Ball", "Bone"]  # more may join later (e.g. tug rope)

def toy_menu_entries(anchor_pos):
    """Rects for each option, clamped so the menu stays on-screen. Computed
    fresh on each access, same reasoning as context_menu_entries."""
    w, h = CONTEXT_MENU_OPTION_SIZE
    x = min(anchor_pos[0], screen.get_width() - w)
    y = min(anchor_pos[1], screen.get_height() - h * len(TOY_MENU_OPTIONS))
    entries = []
    for i, label in enumerate(TOY_MENU_OPTIONS):
        entries.append((pygame.Rect(x, y + i * h, w, h), label))
    return entries

def draw_toy_menu(anchor_pos):
    for rect, label in toy_menu_entries(anchor_pos):
        draw_button(rect, label)

# --- Main loop -----------------------------------------------------------------

while running:
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
            if context_menu_pos is not None:
                # The context menu swallows this frame's clicks/Esc rather
                # than falling through to normal play controls, so a click
                # meant to dismiss it can't also feed/pet/etc.
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    context_menu_pos = None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, label in context_menu_entries(context_menu_pos):
                        if rect.collidepoint(event.pos):
                            if label == "Call":
                                pet.call_to(context_menu_pos)
                            elif label == "Pet":
                                pet.pet_interact()
                            elif label == "Fetch":
                                pet.request_fetch()
                            break
                    context_menu_pos = None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    context_menu_pos = pygame.Vector2(event.pos)  # reposition
            elif toy_menu_open:
                # Same swallow-this-frame's-input approach as the context menu.
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    toy_menu_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, label in toy_menu_entries(toy_menu_anchor):
                        if rect.collidepoint(event.pos) and label in TOY_MENU_OPTIONS:
                            kind = label.lower()
                            # Picking the kind that's already out again
                            # removes it (a toggle); picking a different one
                            # swaps it out rather than needing two clicks.
                            if toy.active and toy.kind == kind:
                                toy.active = False
                            else:
                                toy.active = True
                                toy.kind = kind
                                toy.place(TOY_DEFAULT_POS)
                            break
                    toy_menu_open = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = STATE_PAUSED
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                context_menu_pos = pygame.Vector2(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Checked in the same front-to-back order draw_scene() draws
                # them (the toy topmost among items, then the toybox/static
                # items underneath), so a click on an overlap resolves to
                # whatever is actually on top. Petting moved to the
                # right-click menu specifically so it can never compete here -
                # the pet is drawn on top of everything, so left-click would
                # otherwise always win on any overlap (e.g. a fetched toy
                # sitting right at its feet).
                if toy.active and toy.on_ground and toy.contains_point(event.pos):
                    toy.throw_toward(event.pos)
                elif toybox.contains_point(event.pos):
                    toy_menu_open = True
                    toy_menu_anchor = pygame.Vector2(
                        toybox.pos.x - CONTEXT_MENU_OPTION_SIZE[0] / 2,
                        toybox.get_rect().top - CONTEXT_MENU_OPTION_SIZE[1] * len(TOY_MENU_OPTIONS) - 8,
                    )
                elif food.get_rect().collidepoint(event.pos):
                    pet.feed()
                elif water.get_rect().collidepoint(event.pos):
                    pet.give_water()

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
                    name_input = DEFAULT_PET_NAME
                    toy.active = False
                    toy_menu_open = False
                    state = STATE_MENU

        elif state == STATE_LOAD:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = STATE_PAUSED
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if LOAD_BACK_BUTTON_RECT.collidepoint(event.pos):
                    state = STATE_PAUSED
                else:
                    for rect, saved_name in load_menu_entries():
                        if rect.collidepoint(event.pos):
                            safe_save()  # keep the outgoing pet's progress
                            start_pet(saved_name)
                            state = STATE_PLAYING
                            break

    if state == STATE_MENU:
        draw_menu()

    elif state == STATE_PLAYING:
        toy_pos = toy.pos if toy.active else None
        # A carried toy is held, not falling - physics is paused for it and
        # its position instead follows the pet directly, below.
        if toy.active and not pet.carrying_toy:
            toy.physics_update(dt, GROUND_Y, screen.get_width())
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        toy_on_ground = toy.active and toy.on_ground and not pet.carrying_toy
        pet.update(dt, food.pos, water.pos, toy_pos, bed.pos, toy_on_ground, mouse_pos, toybox.pos)

        if pet.wants_to_throw_toy:
            # The pet decided to play by itself - same random toss as a
            # player click on the toy (player throws are deterministic -
            # see toy.throw_toward() - since the pet isn't "aiming").
            throw_velocity = pygame.Vector2(random.uniform(-450, 450), random.uniform(-650, -450))
            toy.throw(throw_velocity)
            pet.wants_to_throw_toy = False
        if pet.wants_toy_from_box:
            toy.active = True
            toy.place(TOY_DEFAULT_POS)
            pet.wants_toy_from_box = False
        if pet.carrying_toy:
            toy.pos = pet.mouth_pos()
        if pet.wants_to_drop_toy:
            toy.place(pygame.Vector2(pet.pos.x, GROUND_Y))
            pet.wants_to_drop_toy = False
        if pet.fetch_delivered:
            wallet.earn(pet.fetch_reward_amount)
            pet.fetch_delivered = False

        draw_scene()
        if context_menu_pos is not None:
            draw_context_menu(context_menu_pos)
        if toy_menu_open:
            draw_toy_menu(toy_menu_anchor)

        autosave_timer += dt
        if autosave_timer >= AUTOSAVE_INTERVAL:
            safe_save()
            autosave_timer = 0

    elif state == STATE_PAUSED:
        # World is frozen: draw the last state without updating it.
        draw_scene()
        draw_pause_menu()

    elif state == STATE_LOAD:
        draw_load_menu(load_menu_entries())

    # flip() the display to put your work on screen
    pygame.display.flip()

    # limits FPS to 60
    # dt is delta time in seconds since last frame, used for framerate-
    # independent physics.
    dt = clock.tick(60) / 1000

safe_save()
pygame.quit()
