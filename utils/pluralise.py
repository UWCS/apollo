def pluralise(l, word, single="", plural="s"):
    if len(l) > 1:
        return word + plural
    else:
        return word + single