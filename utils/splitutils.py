from typing import List
import re


def chunk(list: List, chunk_size=20) -> List[List]:
    chunk_size = max(1, chunk_size)
    return [list[i : i + chunk_size] for i in range(0, len(list), chunk_size)]


def split_embeds(lines):
    pass


def split_args(input: str, delimiter=";", ignore_escaped=False) -> List[str]:
    if ignore_escaped:
        return input.split(delimiter)
    else:
        return [x.strip() for x in re.split(r"(?<!\\); ?", input)]
