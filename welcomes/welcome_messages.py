from random import choice

from favourite_things import generate_category

# Greeting phrases to prepend to messages
GREETINGS = ["Hi", "Hiya", "Howdy", "Hello", "Greetings", "Welcome"]


def generate_welcome_message(name, channel):
    return "{} {}!\nIf you want, feel free to introduce yourself in {} with your pronouns, interests, and {}".format(
        choice(GREETINGS), name, channel, generate_category()
    )
