import re
from csv import QUOTE_ALL, Sniffer, reader
from typing import List

import _csv


# Customized sniffer with custom delimiter order
class ArgSniffer(Sniffer):
    def __init__(self, preferred):
        super().__init__()
        self.preferred = preferred


# Default delimiter order
delimiters = ["\n", ";", ",", " "]

# Split voting choice arguments
def split_args(input: str, dels=None) -> List[str]:
    if dels is None:
        dels = delimiters

    if "\n" in input:
        split = input.split("\n")
    else:
        # Use CSV sniffer to find delimiter
        try:
            dia = ArgSniffer(dels).sniff(input)
            dia.skipinitialspace = True
            dia.escapechar = "\\"
            dia.quoting = QUOTE_ALL
            delim = str(dia.delimiter)
        except _csv.Error:  # No delimiter present
            return [input] if input else []

        # If picked something else, ignore
        if delim not in dels:
            return [input] if input else []

        # If delimiter is only ever escaped, re-search for others
        # e.g. "a, b\; c, d" should be ["a", "b; c", "d"] not ["a, b\" "c, d"] or ["a, b; c, d"]
        # It's a bit of a hack, but only alternative is copying and editing csv.Sniffer
        if not re.search(r"(?<!\\)" + re.escape(delim), input):
            if not dels:
                return [input]
            return split_args(input, dels[dels.index(delim) + 1 :])

        split = next(reader([input], dialect=dia))

    return [x.strip() for x in split if x.strip()]
