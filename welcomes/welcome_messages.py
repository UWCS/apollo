from random import choice, choices

# Greeting phrases to prepend to messages
GREETINGS = ["Hi", "Hiya", "Howdy", "Hello", "Greetings", "Welcome"]


# Categories of favourite things
class Category:
    def __init__(self, weight, template, selection):
        self.weight = weight
        self.template = template
        self.selection = selection
    def generate(self):
        return self.template.format(choice(self.selection))

categories = []


MISC = [
    "typo",
    "Doctor Who companion",
    "type of chair",
    "punctuation mark",
    "era of history",
    "paradox",
    "unit of measurement",
    "spacecraft",
    "metal alloy",
    "meme",
    "Twitch streamer",
    "Minecraft block",
    "holiday",
    "artist",
    "colour",
    "letter of the alphabet",
    "song",
    "game"
    "piece of music",
    "fruit",
    "programming language",
]
categories.append(Category(len(MISC), "{}", MISC))


BREED = [
    "breed of dog",
    "breed of cat",
]
categories.append(Category(1, "{}", BREED))


DRINK = [
    "hot drink",
    "cold drink",
]
categories.append(Category(1, "{}", DRINK))


MEDIUM = [
    "music",
    "film",
    "movie",
    "TV show",
    "video game",
    "board game",
]
categories.append(Category(1, "genre of {}", MEDIUM))


FOODSTUFF = [
    "smoothie",
    "milkshake",
    "ice cream",
    "jam",
]
categories.append(Category(1, "flavour of {}", FOODSTUFF))


FILLING = [
    "burrito",
    "pancake",
]
categories.append(Category(1, "{} filling", FILLING))


ANIMAL_CLASS = [
    "mammal",
    "reptile",
    "amphibian",
    "fish",
    "bird",
    "lizard",
    "gastropod",
]
categories.append(Category(1, "species of {}", ANIMAL_CLASS))


ANIMAL_TYPE = [
    "big cat",
    "supernatural creature",
    "dragon",
    "feathered animal",
    "mushroom",
]
categories.append(Category(1, "type of {}", ANIMAL_TYPE))


MYTHOLOGY = [
    "Greek",
    "Egyptian",
    "Roman",
    "Aztec",
]
categories.append(Category(1, "{} god", MYTHOLOGY))


FRANCHISE = [
    "Marvel movie",
    "Harry Potter movie",
    "DC movie",
    "superhero",
    "Pokemon",
    "Star Wars episode or spin-off",
    "episode of the Simpsons",
    "episode of Doctor Who",
    "episode of Game of Thrones",
]
categories.append(Category(1, "{}", FRANCHISE))


BRAND = [
    "cereal",
    "toothpaste",
    "games console",
]
categories.append(Category(1, "brand of {}", FRANCHISE))


# Generate a complete welcome message given a member's name and a intros channel
def generate_welcome_message(name, channel):
    weights = [c.weight for c in categories]
    category = choices(categories, weights)[0]
    return "{} {}!\nIf you want, feel free to introduce yourself in {} with your pronouns, interests, and favourite {}.".format(choice(GREETINGS), name, channel, category.generate ())
