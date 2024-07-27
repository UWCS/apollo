from random import Random

from discord import Intents
from discord.ext.commands import Bot

from cogs.commands.eightball import EightBall


def test_eightball_no_question():
    eightball = EightBall(Bot("/", intents=Intents()), Random(1), [])

    assert (
        eightball.execute("test", [])
        == "test: You must pose the Magic 8-ball a dilemma!"
    )


def test_eightball_question_with_fixed_randomness():
    eightball = EightBall(
        Bot("/", intents=Intents()), Random(1), ["Yes", "No", "Maybe"]
    )

    answers = [
        eightball.execute("test", ["Should", "I", "eat", "cake?"]) for i in range(0, 7)
    ]

    assert answers == [
        "test: Yes",
        "test: Maybe",
        "test: Yes",
        "test: No",
        "test: Yes",
        "test: No",
        "test: No",
    ]
