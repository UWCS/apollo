from config import CONFIG


def get_name_string(message):
    # if message.clean_content.startswith("**<"): <-- FOR TESTING
    if message.author.id == CONFIG["UWCS_DISCORD_BRIDGE_BOT_ID"]:
        return message.clean_content.split(" ")[0][3:-3]
    else:
        return f"{message.author.mention}"


def pluralise(l, word, single="", plural="s"):
    if len(l) > 1:
        return word + plural
    else:
        return word + single
