#!/usr/bin/python3
# npc.py

import os
import sys
import json
import pygame
import random as rand
import numpy as np

from npc_net import NPCAgent
import vocalizations

BASE_DIR=os.path.dirname(__file__)
SAVE_DIR = os.path.join(BASE_DIR, "saves")

# Personality/need-knob fields persisted alongside the DQN weights.
PERSONALITY_FIELDS = [
    "open", "conscient", "extravers", "agreeable", "neuroticism",
    "hunger_threshold", "thirst_threshold", "boredom_threshold", "tiredness_threshold",
    "satiated_threshold", "interact_radius", "arrival_radius",
    "hunger_drain_rate", "thirst_drain_rate", "boredom_drain_rate", "tiredness_drain_rate",
    "happiness_decay_rate", "happiness_play_rate", "pet_happiness_boost", "pet_cooldown",
    "fetch_affinity",
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

# Idle-time self-initiated behavior: when nothing is urgent and the pet
# hasn't been called, it picks one of these (weighted by personality - see
# _idle_weight) instead of just standing frozen in place, walks there,
# lingers for a randomized duration in the range below, then picks again.
IDLE_STAND_HOLD = (3, 6)             # seconds spent just standing before deciding again
IDLE_WANDER_HOLD = (2, 4)            # seconds spent loitering after wandering somewhere
IDLE_BED_HOLD = (5, 9)               # seconds spent resting on the bed
IDLE_SELF_PLAY_HOLD = (0.3, 0.6)     # brief pause before throwing the toy itself
IDLE_FETCH_PICKUP_HOLD = (0.2, 0.4)  # brief pause picking the toy up before carrying it over
IDLE_GET_TOY_HOLD = (0.3, 0.6)       # brief pause "grabbing" a toy out of the toybox

# Teaching fetch: petting the pet shortly after it delivers a fetched toy is
# a reward that nudges its odds toward choosing fetch over self-play next
# time (on top of the base personality weight in _idle_weight), and slowly
# fades if you stop reinforcing it - a taught habit, not a one-time switch.
FETCH_AFFINITY_MAX = 4.0          # cap - comparable to a trait's max weight contribution
FETCH_AFFINITY_REWARD = 0.75      # bump per rewarded pet
FETCH_AFFINITY_DECAY_RATE = 0.02  # per second - ~a few minutes to fully fade if never reinforced
FETCH_REWARD_WINDOW = 6           # seconds after a delivery during which petting counts as reinforcement

# Fetch mini-game currency (see wallet.py, which owns the actual balance -
# npc.py only computes how much a delivery is worth and signals it via
# fetch_delivered/fetch_reward_amount). Flat for the first couple of
# deliveries in a streak, then ramps up fast - streaks are meant to be rare
# and worth chasing, not a long grind. self.fetch_streak counts consecutive
# deliveries and resets the moment anything other than fetch (or the
# get_toy lead-up to a commanded fetch) gets picked - see _pick_idle_activity.
FETCH_STREAK_REWARDS = [5, 5, 6, 15, 45]  # coins for the Nth consecutive delivery (index 0 = 1st)
FETCH_STREAK_GROWTH = 3                   # beyond the table, keep multiplying by this per extra streak step
FETCH_AUTONOMOUS_REWARD_RATIO = 0.5       # a delivery the pet chose on its own pays less than one you commanded

# Vocalizations: a speech bubble (onomatopoeia + emotion emoji, see
# vocalizations.py) the pet shows for a few seconds, on a cooldown so it
# doesn't spam. Which one it's allowed to show depends on a mutually
# exclusive read of its current emotion (_current_emotion) - e.g. a badly
# neglected pet reads as angry, not sad, so it growls instead of whining.
VOCAL_COOLDOWN = (4, 9)      # seconds between vocalizations, randomized so it isn't metronomic
VOCAL_DISPLAY_TIME = 2.5     # seconds the speech bubble stays up
ANGRY_HAPPINESS_MAX = 15     # happiness at/below this reads as angry - takes priority over sad/lonely
SAD_HAPPINESS_MAX = 40       # + an urgent physical need (hunger/thirst/tiredness) reads as sad
LONELY_HAPPINESS_MAX = 30    # neglected but no physical need reads as lonely
HAPPY_HAPPINESS_MIN = 75     # ambient mood good enough for a spontaneous happy bark

STATE_SIZE = 4   # [npc.x, npc.y, target.x, target.y], all normalized to 0-1
ACTION_SIZE = 3  # 0: move left, 1: stay, 2: move right

# --- Sprite animation (temporary placeholder art from DogBundle) -----------
# Corgi.png is a 512x192 sheet: 8 cols x 3 rows of 64x64 frames. Row 0 is an
# 8-frame walk cycle, row 1 an 8-frame idle, row 2 a 6-frame sit (the sheet's
# last 2 sit cells are empty). Sprite art faces right natively.
SPRITE_PATH = os.path.join(BASE_DIR, "DogBundle", "PNGs", "Corgi.png")
SPRITE_FRAME_SIZE = 64
SPRITE_DRAW_SIZE = 144  # scaled up from the native 64px frames
SPRITE_ROWS = {"walk": 0, "idle": 1, "sit": 2}
SPRITE_FRAME_COUNTS = {"walk": 8, "idle": 8, "sit": 6}
ANIM_FPS = 8
# Every frame in the sheet has ~16px of transparent padding below the paws
# (measured directly), so anchoring on the raw frame bottom would float the
# sprite above the ground - shift the anchor down by that much, scaled.
SPRITE_BOTTOM_PADDING = round(16 * SPRITE_DRAW_SIZE / SPRITE_FRAME_SIZE)

_sprite_cache = None  # populated lazily so loading happens after pygame.display is set up

def _load_sprite_frames():
    global _sprite_cache
    if _sprite_cache is not None:
        return _sprite_cache

    sheet = pygame.image.load(SPRITE_PATH).convert_alpha()
    cache = {"left": {}, "right": {}}
    for anim_state, row in SPRITE_ROWS.items():
        frames_native = []  # native sheet orientation - faces right
        for col in range(SPRITE_FRAME_COUNTS[anim_state]):
            rect = pygame.Rect(col * SPRITE_FRAME_SIZE, row * SPRITE_FRAME_SIZE,
                                SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE)
            frame = sheet.subsurface(rect).copy()
            frame = pygame.transform.scale(frame, (SPRITE_DRAW_SIZE, SPRITE_DRAW_SIZE))
            frames_native.append(frame)
        cache["right"][anim_state] = frames_native
        cache["left"][anim_state] = [pygame.transform.flip(f, True, False) for f in frames_native]

    _sprite_cache = cache
    return cache

_bubble_font_cache = None  # populated lazily for the same reason as _sprite_cache

def _bubble_font():
    global _bubble_font_cache
    if _bubble_font_cache is None:
        _bubble_font_cache = pygame.font.SysFont(None, 26)
    return _bubble_font_cache


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
        self.called = False  # True after the player uses the right-click "Call" option
        self.call_pos = None

        # Idle-time self-initiated behavior (see _tick_idle/_pick_idle_activity).
        self.idle_activity = None  # None (standing) / "stand" / "wander" / "bed" / "self_play" / "fetch"
        self.idle_target = pygame.Vector2(self.pos)
        self._idle_hold_timer = 0
        self._fetch_phase = None  # "pickup" or "deliver", only meaningful during idle_activity == "fetch"
        self.carrying_toy = False       # True while mid-fetch, walking the toy toward the player
        self.wants_to_throw_toy = False # set for one frame when self-play decides to throw - virt-pet.py acts on it and clears it
        self.wants_to_drop_toy = False  # set for one frame when a fetch delivery (or interruption) ends - same pattern
        self.wants_toy_from_box = False # set for one frame when "get_toy" decides to grab one - same pattern

        # Learned fetch preference (see pet_interact()/FETCH_* constants) -
        # persisted so training carries over between sessions.
        self.fetch_affinity = 0.0
        self._fetch_reward_window = 0  # seconds left during which petting counts as fetch reinforcement

        # Fetch mini-game (see request_fetch()/_pick_idle_activity/_tick_idle).
        self.fetch_requested = False  # True after the player uses the right-click "Fetch" option
        self.fetch_commanded = False  # whether the CURRENT/most recent fetch round was commanded (vs. autonomous)
        self.fetch_streak = 0         # consecutive successful deliveries - not persisted, resets each session
        self.fetch_delivered = False       # set for one frame on a successful delivery - virt-pet.py acts on it and clears it
        self.fetch_reward_amount = 0       # coins earned by that delivery, valid alongside fetch_delivered

        # Vocalizations (see _tick_vocalization/_current_emotion). species
        # picks which vocabulary (vocalizations.py) applies - hardcoded for
        # now since only the dog/Corgi is wired up; once other species
        # exist this becomes a real per-pet choice (and should join
        # PERSONALITY_FIELDS so it persists).
        self.species = vocalizations.DOG
        self.vocalization = None  # None, or {"text": ..., "emoji": ...} - the current speech bubble
        self._vocal_cooldown = 0
        self._vocal_display_timer = 0

        self._sprite_frames = _load_sprite_frames()
        self.anim_state = "idle"  # "walk", "idle", or "sit"
        self.anim_frame = 0
        self.anim_timer = 0
        self.facing_left = True  # sprite art's native orientation

        self.agent = NPCAgent(STATE_SIZE, ACTION_SIZE)
        self.last_state = None
        self.last_action = None

        # Resume a previously saved pet (brain + personality) if one exists
        # for this name; otherwise roll a fresh personality.
        if not self.load():
            self.randomize_personality()

    def randomize_personality(self):
        # See _idle_weight() for how these currently shape behavior.
        self.open = rand.randint(3, 6)
        self.conscient = rand.randint(3, 5)
        self.extravers = rand.randint(4, 8)
        self.agreeable = rand.randint(4, 6)
        self.neuroticism = rand.randint(0, 2)

    def _advance_animation(self, dt):
        if self.move < 0:
            self.facing_left = True
        elif self.move > 0:
            self.facing_left = False
        # move == 0: keep whichever direction it was last facing.

        if self.move != 0:
            new_state = "walk"
        elif self.active_need == "tiredness" or self.idle_activity == "bed":
            new_state = "sit"
        else:
            new_state = "idle"  # includes eating/drinking - no dedicated animation for those

        if new_state != self.anim_state:
            self.anim_state = new_state
            self.anim_frame = 0
            self.anim_timer = 0

        frame_count = SPRITE_FRAME_COUNTS[self.anim_state]
        self.anim_timer += dt
        frame_duration = 1 / ANIM_FPS
        while self.anim_timer >= frame_duration:
            self.anim_timer -= frame_duration
            self.anim_frame = (self.anim_frame + 1) % frame_count

    def draw(self):
        orientation = "left" if self.facing_left else "right"
        frames = self._sprite_frames[orientation][self.anim_state]
        frame = frames[self.anim_frame % len(frames)]
        # pos.y is the pet's center (matches the old collision circle); the
        # sprite's feet should land where that circle's bottom edge was, so
        # compensate for the frame's built-in transparent bottom padding.
        anchor_y = self.pos.y + 40 + SPRITE_BOTTOM_PADDING
        rect = frame.get_rect(midbottom=(round(self.pos.x), round(anchor_y)))
        self.screen.blit(frame, rect)

        if self.vocalization is not None:
            self._draw_bubble(f"{self.vocalization['text']} {self.vocalization['emoji']}")
        elif self.anim_state == "sit":
            # "sit" only ever fires once actually settled at the bed - both
            # for urgent tiredness and for proactive "bed" idle napping (see
            # _advance_animation) - so it doubles as "is asleep" here.
            self._draw_bubble("ZzZzZz")

    def _draw_bubble(self, label):
        font = _bubble_font()
        text_surf = font.render(label, True, "black")
        bubble_rect = text_surf.get_rect().inflate(16, 12)
        bubble_rect.midbottom = (round(self.pos.x), round(self.pos.y - 75))  # just above the sprite's head
        pygame.draw.rect(self.screen, "white", bubble_rect, border_radius=10)
        pygame.draw.rect(self.screen, "black", bubble_rect, 2, border_radius=10)
        self.screen.blit(text_surf, text_surf.get_rect(center=bubble_rect.center))

    def mouth_pos(self):
        """Approximate position of the pet's mouth, in front of it in
        whichever direction it's facing - used to render a carried item
        (the fetched toy) glued roughly where it'd actually be held."""
        x_offset = -12 if self.facing_left else 12
        return pygame.Vector2(self.pos.x + x_offset, self.pos.y + 30)

    def _current_emotion(self):
        """A mutually-exclusive read of the pet's current emotional state,
        most specific/urgent first - only one is ever "true" at once, so
        e.g. a badly-neglected pet reads as angry rather than sad, and
        growls instead of whining. Returns None when nothing's notable
        enough to vocalize about."""
        if self.happiness <= ANGRY_HAPPINESS_MAX:
            return "angry"
        if self.active_need in ("hunger", "thirst", "tiredness") and self.happiness <= SAD_HAPPINESS_MAX:
            return "sad"
        if self.happiness <= LONELY_HAPPINESS_MAX:
            return "lonely"
        if self.happiness >= HAPPY_HAPPINESS_MIN:
            return "happy"
        return None

    def _try_vocalize(self, emotion):
        """Shows a speech bubble for `emotion` if the pet's species has
        vocab for it and the cooldown has elapsed; otherwise a silent
        no-op, so callers (event-triggered barks, the periodic emotion
        check) don't need to check anything themselves first."""
        if self._vocal_cooldown > 0:
            return
        entry = vocalizations.VOCABULARY.get(self.species, {}).get(emotion)
        if entry is None:
            return
        self.vocalization = {"text": entry["text"], "emoji": entry["emoji"]}
        self._vocal_display_timer = VOCAL_DISPLAY_TIME
        self._vocal_cooldown = rand.uniform(*VOCAL_COOLDOWN)

    def _tick_vocalization(self, dt):
        self._vocal_cooldown = max(0, self._vocal_cooldown - dt)
        if self._vocal_display_timer > 0:
            self._vocal_display_timer -= dt
            if self._vocal_display_timer <= 0:
                self.vocalization = None

        if self.anim_state == "sit":
            # Asleep - the ZzZzZz bubble (see draw()) takes over instead;
            # clear anything left over so the two bubbles never overlap.
            self.vocalization = None
            return

        emotion = self._current_emotion()
        if emotion is not None:
            self._try_vocalize(emotion)

    def pet_interact(self):
        """Called when the player pets the pet (right-click menu). Returns
        True if it registered (subject to a cooldown so spam-clicking can't
        max out happiness instantly). Petting shortly after a fetch
        delivery also counts as reinforcement - see FETCH_REWARD_WINDOW."""
        if self._pet_cooldown > 0:
            return False
        self.happiness = min(100, self.happiness + self.pet_happiness_boost)
        self._pet_cooldown = self.pet_cooldown
        if self._fetch_reward_window > 0:
            self.fetch_affinity = min(FETCH_AFFINITY_MAX, self.fetch_affinity + FETCH_AFFINITY_REWARD)
            self._fetch_reward_window = 0  # one reward per delivery, not per pet within the window
        self._try_vocalize("happy")
        return True

    def feed(self):
        """Called when the player clicks the food item - feeds the pet
        directly, wherever it currently is, instead of waiting for it to
        walk over and drain hunger via proximity."""
        self.hunger = 0

    def give_water(self):
        """Called when the player clicks the water item - see feed()."""
        self.thirst = 0

    def call_to(self, pos):
        """Called when the player picks "Call" from the right-click context
        menu - the pet will walk to pos once it's done with anything more
        urgent (see choose_target)."""
        self.call_pos = pygame.Vector2(pos)
        self.called = True

    def request_fetch(self):
        """Called when the player picks "Fetch" from the right-click context
        menu - same deferral pattern as call_to(): takes effect once nothing
        more urgent is going on. Grabs a toy from the toybox first if none is
        out (see _pick_idle_activity), then fetches once one is available."""
        self.fetch_requested = True

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

    def choose_target(self, dt, food_pos, water_pos, toy_pos, bed_pos, toy_on_ground, mouse_pos, toybox_pos):
        # need name -> (current value, seek threshold, target position)
        # Tiredness heads for the bed, same as hunger/thirst head for
        # food/water - falls back to standing in place if there's no bed
        # (defensive; virt-pet.py always passes one).
        tiredness_target = pygame.Vector2(bed_pos) if bed_pos is not None else pygame.Vector2(self.pos)
        needs = {
            "hunger": (self.hunger, self.hunger_threshold, food_pos),
            "thirst": (self.thirst, self.thirst_threshold, water_pos),
            "tiredness": (self.tiredness, self.tiredness_threshold, tiredness_target),
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
        if urgent:
            name, _, target = max(urgent, key=lambda n: n[1])
            self.active_need = name
            self._abandon_idle_activity()
            return target

        # Nothing urgent: head for wherever the player last called the pet
        # to, if anywhere; otherwise pursue (or pick) a self-initiated idle
        # activity instead of just standing frozen in place.
        if self.called and self.call_pos is not None:
            self._abandon_idle_activity()
            return self.call_pos

        self._tick_idle(dt, bed_pos, toy_pos, toy_on_ground, mouse_pos, toybox_pos)
        return self.idle_target

    def _idle_weight(self, choice):
        """Personality-weighted odds for each idle-time activity - a higher
        self.<trait> (0-10 scale) makes that activity more likely to be
        picked without ever ruling the others out entirely. fetch also
        carries self.fetch_affinity, a learned (not personality-fixed)
        preference from being rewarded for delivering - see pet_interact()."""
        if choice == "bed":
            return 1.0 + self.conscient * 0.3   # organized/self-controlled pets rest more deliberately
        if choice == "wander":
            return 1.0 + self.open * 0.3        # curious pets explore more
        if choice == "self_play":
            return 1.0                          # the "default" when nothing else pulls harder
        if choice in ("fetch", "get_toy"):
            # Sociable, cooperative pets would rather play WITH you than
            # alone - extraversion pulls toward fetch, not self-play.
            return 1.0 + self.agreeable * 0.3 + self.extravers * 0.2 + self.fetch_affinity
        return 1.0 + self.neuroticism * 0.3     # "stand" - anxious pets stay put more

    def _pick_idle_activity(self, bed_pos, toy_pos, toy_on_ground, toybox_pos):
        # Every fresh pick starts "uncommanded" - only the forced-fetch
        # branch below flips this True, so a delivery's reward always
        # reflects how *that* round actually started, never a stale flag
        # left over from an earlier one.
        self.fetch_commanded = False

        # A player-issued "Fetch" command (see request_fetch()) overrides
        # the usual weighted roll entirely - straight to fetch if a toy's
        # ready, or to get_toy first (leaving fetch_requested set so the
        # *next* pick, once a toy exists, resolves to fetch automatically -
        # no extra chaining logic needed beyond not clearing the flag here).
        if self.fetch_requested:
            if toy_pos is not None and toy_on_ground:
                self.idle_activity = "fetch"
                self.fetch_commanded = True
                self.fetch_requested = False
                self.idle_target = pygame.Vector2(toy_pos)
                self._idle_hold_timer = rand.uniform(*IDLE_FETCH_PICKUP_HOLD)
                self._fetch_phase = "pickup"
                return
            elif toybox_pos is not None:
                self.idle_activity = "get_toy"
                self.idle_target = pygame.Vector2(toybox_pos)
                self._idle_hold_timer = rand.uniform(*IDLE_GET_TOY_HOLD)
                return
            else:
                self.fetch_requested = False  # nothing to fetch and no way to get one - drop it

        choices = ["stand", "wander"]
        if bed_pos is not None:
            choices.append("bed")
        if toy_pos is not None and toy_on_ground:
            choices.append("self_play")
            choices.append("fetch")
        elif toybox_pos is not None:
            # No toy out right now, but there's a box to grab one from -
            # "wanting to play" first means fetching a toy to play with.
            choices.append("get_toy")
        weights = [self._idle_weight(c) for c in choices]
        self.idle_activity = rand.choices(choices, weights=weights, k=1)[0]

        # A streak is consecutive fetch deliveries specifically - anything
        # else the pet chooses to do instead breaks it. get_toy doesn't,
        # since a commanded fetch routes through it on the way to fetching.
        if self.idle_activity not in ("fetch", "get_toy"):
            self.fetch_streak = 0

        if self.idle_activity == "bed":
            self.idle_target = pygame.Vector2(bed_pos)
            self._idle_hold_timer = rand.uniform(*IDLE_BED_HOLD)
        elif self.idle_activity == "wander":
            w = self.screen.get_width()
            self.idle_target = pygame.Vector2(rand.uniform(60, w - 60), self.pos.y)
            self._idle_hold_timer = rand.uniform(*IDLE_WANDER_HOLD)
        elif self.idle_activity == "self_play":
            self.idle_target = pygame.Vector2(toy_pos)
            self._idle_hold_timer = rand.uniform(*IDLE_SELF_PLAY_HOLD)
        elif self.idle_activity == "fetch":
            self.idle_target = pygame.Vector2(toy_pos)
            self._idle_hold_timer = rand.uniform(*IDLE_FETCH_PICKUP_HOLD)
            self._fetch_phase = "pickup"
        elif self.idle_activity == "get_toy":
            self.idle_target = pygame.Vector2(toybox_pos)
            self._idle_hold_timer = rand.uniform(*IDLE_GET_TOY_HOLD)
        else:  # "stand"
            self.idle_target = pygame.Vector2(self.pos)
            self._idle_hold_timer = rand.uniform(*IDLE_STAND_HOLD)

    def _tick_idle(self, dt, bed_pos, toy_pos, toy_on_ground, mouse_pos, toybox_pos):
        """Advances self-initiated idle behavior - only reached from
        choose_target when nothing is urgent and the pet hasn't been
        called. Picks an activity when idle, walks to it, lingers there for
        a bit (or, for fetch's delivery leg, until it reaches the player),
        then picks again."""
        if self.idle_activity is None:
            self._pick_idle_activity(bed_pos, toy_pos, toy_on_ground, toybox_pos)
            return

        # A toy that disappeared mid-activity (e.g. toggled off from the
        # toybox) shouldn't leave the pet marching toward - or "delivering"
        # - something that no longer exists.
        if self.idle_activity in ("self_play", "fetch") and toy_pos is None:
            self._abandon_idle_activity()
            return

        if self.idle_activity == "fetch" and self._fetch_phase == "deliver" and mouse_pos is not None:
            self.idle_target = pygame.Vector2(mouse_pos)  # live-track the player while carrying it over

        arrived = abs(self.pos.x - self.idle_target.x) <= self.arrival_radius
        if not arrived:
            return

        self._idle_hold_timer -= dt
        if self._idle_hold_timer > 0:
            return

        if self.idle_activity == "self_play":
            self.wants_to_throw_toy = True
            self.idle_activity = None
            self._try_vocalize("happy")
        elif self.idle_activity == "get_toy":
            self.wants_toy_from_box = True
            self.idle_activity = None
        elif self.idle_activity == "fetch" and self._fetch_phase == "pickup":
            self.carrying_toy = True
            self._fetch_phase = "deliver"
            self.idle_target = pygame.Vector2(mouse_pos) if mouse_pos is not None else pygame.Vector2(self.pos)
            self._idle_hold_timer = 0  # deliver phase ends on arrival at the player, not a timer
            self._try_vocalize("happy")
        elif self.idle_activity == "fetch":  # deliver phase, arrived at the player
            self.carrying_toy = False
            self.wants_to_drop_toy = True
            self.idle_activity = None
            self._fetch_phase = None
            self._fetch_reward_window = FETCH_REWARD_WINDOW  # petting now counts as reinforcement
            self.fetch_streak += 1
            self.fetch_reward_amount = self._fetch_reward()
            self.fetch_delivered = True
            self.fetch_commanded = False  # consumed - the next round starts uncommanded until proven otherwise
        else:
            self.idle_activity = None

    def _fetch_reward(self):
        """Coins earned by the delivery that just completed - see the
        FETCH_STREAK_*/FETCH_AUTONOMOUS_REWARD_RATIO constants for the
        shape (flat-then-fast-growing streaks, commanded pays full)."""
        streak = self.fetch_streak
        if streak <= len(FETCH_STREAK_REWARDS):
            base = FETCH_STREAK_REWARDS[streak - 1]
        else:
            base = FETCH_STREAK_REWARDS[-1] * (FETCH_STREAK_GROWTH ** (streak - len(FETCH_STREAK_REWARDS)))
        return base if self.fetch_commanded else round(base * FETCH_AUTONOMOUS_REWARD_RATIO)

    def _abandon_idle_activity(self):
        """Interrupts any in-progress idle activity - e.g. an urgent need
        just became active, or the player called the pet. If it was
        mid-fetch, drop the toy where it stands rather than leaving it
        glued to the pet with nothing ever placing it back down."""
        if self.idle_activity == "fetch":
            self.fetch_streak = 0  # an interrupted delivery breaks the chain
        if self.carrying_toy:
            self.carrying_toy = False
            self.wants_to_drop_toy = True
        self.idle_activity = None
        self._fetch_phase = None
        self.fetch_commanded = False

    def update(self, dt, food_pos, water_pos, toy_pos=None, bed_pos=None, toy_on_ground=False,
               mouse_pos=None, toybox_pos=None):
        self._pet_cooldown = max(0, self._pet_cooldown - dt)
        self._fetch_reward_window = max(0, self._fetch_reward_window - dt)
        self.fetch_affinity = max(0.0, self.fetch_affinity - FETCH_AFFINITY_DECAY_RATE * dt)

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
        # Like hunger/thirst, tiredness only recovers once actually at the
        # bed - not just anywhere along the way there. bed_pos is None only
        # in the absence of a bed at all (defensive), in which case fall
        # back to recovering in place rather than getting stuck tired forever.
        if self.active_need == "tiredness":
            at_bed = bed_pos is None or self.pos.distance_to(bed_pos) <= self.interact_radius
            if at_bed:
                self.tiredness = max(0, self.tiredness - self.tiredness_drain_rate * dt)

        target_pos = self.target_pos = self.choose_target(dt, food_pos, water_pos, toy_pos, bed_pos, toy_on_ground, mouse_pos, toybox_pos)

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

        # A call is fulfilled once the pet arrives with nothing more urgent
        # pulling it elsewhere (self.active_need is None precisely when
        # choose_target picked the call target over an urgent need).
        if self.called and arrived and self.active_need is None:
            self.called = False
            self._try_vocalize("happy")

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

        self._advance_animation(dt)
        self._tick_vocalization(dt)

        if self.verbose:
            print(f"action={action} move={self.move} reward={reward:.3f} epsilon={self.agent.epsilon:.3f} "
                  f"hunger={self.hunger:.1f} thirst={self.thirst:.1f} boredom={self.boredom:.1f} "
                  f"tiredness={self.tiredness:.1f} happiness={self.happiness:.1f}")

