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


GENERIC = [
    "instrument",
    "movie",
    "book",
    "author",
    "actor",
    "song",
    "game",
    "piece of music",
    "artist",
    "colour",
]
categories.append(Category(len(GENERIC), "{}", GENERIC))


MISC = [
    "typo",
    "punctuation mark",
    "era of history",
    "paradox",
    "unit of measurement",
    "spacecraft",
    "meme",
    "Twitch streamer",
    "Minecraft block",
    "month",
    "holiday",
    "letter of the alphabet",
    "fruit",
    "programming language",
    "continent",
    "flag",
    "cardinal direction",
    "planet",
    "piece of cutlery",
    "utensil",
    "ancient, modern, or natural wonder of the world",
    "font",
    "constellation",
    "type of maze",
    "olympic sport",
    "word beginning and ending with the same letter",
    "animated character",
    "shape",
    "fact",
    "weather",
]
categories.append(Category(len(MISC), "{}", MISC))


BREED = ["breed of dog", "breed of cat"]
categories.append(Category(1, "{}", BREED))


DRINK = ["drink", "hot drink", "cold drink"]
categories.append(Category(1, "{}", DRINK))


MEDIUM = ["music", "film", "movie", "TV show", "game"]
categories.append(Category(1, "genre of {}", MEDIUM))


GAME_TYPE = ["video game", "board game", "card game"]
categories.append(Category(1, "{}", GAME_TYPE))


FOODSTUFF = ["smoothie", "milkshake", "ice cream", "jam", "crisps"]
categories.append(Category(1, "flavour of {}", FOODSTUFF))


FILLING = ["burrito", "pancake", "studel", "pie"]
categories.append(Category(1, "{} filling", FILLING))


ANIMAL_CLASS = ["mammal", "reptile", "amphibian", "fish", "bird", "lizard", "gastropod"]
categories.append(Category(1, "species of {}", ANIMAL_CLASS))


ANIMAL_TYPE = ["big cat", "supernatural creature", "dragon", "feathered animal"]
categories.append(Category(1, "type of {}", ANIMAL_TYPE))


PLANT_TYPE = [
    "flower",
    "tree",
    "mushroom",
    "deciduous tree",
    "evergreen tree",
    "forest",
]
categories.append(Category(1, "kind of {}", PLANT_TYPE))


MYTHOLOGY = ["Greek", "Egyptian", "Roman", "Aztec"]
categories.append(Category(1, "{} god", MYTHOLOGY))


FRANCHISE = [
    "Marvel movie",
    "Harry Potter movie",
    "DC movie",
    "superhero",
    "Pokemon",
    "Star Wars episode or spin-off",
    "episode of the Simpsons",
    "Doctor Who companion",
    "Game of Thrones character",
]
categories.append(Category(1, "{}", FRANCHISE))


BRAND = ["cereal", "toothpaste", "games console"]
categories.append(Category(1, "brand of {}", BRAND))


FURNITURE = ["chair", "sofa"]
categories.append(Category(1, "type of {}", FURNITURE))


NUMBER = ["number", "positive number", "negative number", "fraction", "non-zero number"]
categories.append(Category(1, "{}", NUMBER))


BUILDING = [
    "building",
    "building with windows",
    "ancient building",
    "modern building",
    "building with a spire",
]


SPEECH = ["shout", "whisper"]
categories.append(Category(1, "thing to {}", SPEECH))


CHEMICAL = ["metal alloy", "element", "chemical element", "ore"]
categories.append(Category(1, "{}", CHEMICAL))


CLOTHING = ["hat", "shirt", "shoe"]
categories.append(Category(1, "{}", CLOTHING))


# Generate a complete welcome message given a member's name and a intros channel
def generate_welcome_message(name, channel):
    weights = [c.weight for c in categories]
    category = choices(categories, weights)[0]
    return "{} {}!\nIf you want, feel free to introduce yourself in {} with your pronouns, interests, and favourite {}.".format(
        choice(GREETINGS), name, channel, category.generate()
    )
