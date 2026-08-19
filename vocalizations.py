#!/usr/bin/python3
# vocalizations.py
#
# Per-species vocabulary for the pet's speech-bubble vocalizations
# (onomatopoeia + an emoji standing in for the attached emotion). Kept
# separate from npc.py so a future species (cat, robot, ...) gets its own
# vocab instead of inheriting the dog's bark - npc.py looks up
# VOCABULARY[self.species][emotion] and never hardcodes a sound.

DOG = "dog"

# emotion -> {"text": onomatopoeia, "emoji": emotion emoji}. Emotions are
# mutually exclusive (see npc.py's _current_emotion()) - only one is ever
# "true" at a time, so e.g. an angry dog is never also whining.
VOCABULARY = {
    DOG: {
        "happy":  {"text": "Woof!",   "emoji": "😄"},
        "angry":  {"text": "Grrr…",   "emoji": "😠"},
        "sad":    {"text": "Whine~",  "emoji": "🥺"},
        "lonely": {"text": "Awoooo…", "emoji": "😔"},
    },
}
