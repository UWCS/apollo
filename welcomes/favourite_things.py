from random import choice, choices


class Category:
    def __init__(self, weight, generate):
        self.weight = weight
        self.generate = generate

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
]

categories.append(Category(len(MISC), lambda : choice(MISC)))


BREED = [
    "breed of dog",
    "breed of cat",
]

categories.append(Category(1, lambda : choice(BREED)))


DRINK = [
    "hot drink",
    "cold drink",
]

categories.append(Category(1, lambda : choice(DRINK)))


MEDIUM = [
    "music",
    "film",
    "movie",
    "TV show",
    "video game",
    "board game",
]

categories.append(Category(1, lambda : "genre of {}".format(choice(MEDIUM))))


FOODSTUFF = [
    "smoothie",
    "milkshake",
    "ice cream",
    "jam",
]

categories.append(Category(1, lambda : "flavour of {}".format(choice(FOODSTUFF))))


FILLING = [
    "burrito",
    "pancake",
]

categories.append(Category(1, lambda : "{} filling".format(choice(FILLING))))


ANIMAL_CLASS = [
    "mammal",
    "reptile",
    "amphibian",
    "fish",
    "bird",
    "lizard",
    "gastropod",
]

categories.append(Category(1, lambda : "species of {}".format(choice(ANIMAL_CLASS))))


ANIMAL_TYPE = [
    "big cat",
    "supernatural creature",
    "dragon",
    "feathered animal",
    "mushroom",
]

categories.append(Category(1, lambda : "type of {}".format(choice(ANIMAL_TYPE))))


MYTHOLOGY = [
    "Greek",
    "Egyptian",
    "Roman",
    "Aztec",
]

categories.append(Category(1, lambda : "{} god".format(choice(MYTHOLOGY))))


LETTER = [
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j",
    "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
    "u", "v", "w", "x", "y", "z"
]

categories.append(Category(1, lambda : "word containing the letter {}".format(choice(LETTER).upper())))


def generate_category():
    distribution = map(lambda c : c.weight, categories)
    category = choices(categories, distribution)
    return category[0].generate ()
