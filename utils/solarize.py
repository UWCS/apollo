# -*- coding: utf-8 -*-

"""solarized.py

Adust matplotlibs rcParams to use solarized colors.
    light()
    dark()
Provides a way to generate color gradients.
    gradient()

"""

__author__ = "Stephan Porz"

import matplotlib as mpl
import numpy as np
from cycler import cycler

COLOR = {
    "base03": "#002B36",
    "base02": "#073642",
    "base01": "#586e75",
    "base00": "#657b83",
    "base0": "#839496",
    "base1": "#93a1a1",
    "base2": "#EEE8D5",
    "base3": "#FDF6E3",
    "yellow": "#B58900",
    "orange": "#CB4B16",
    "red": "#DC322F",
    "magenta": "#D33682",
    "violet": "#6C71C4",
    "blue": "#268BD2",
    "cyan": "#2AA198",
    "green": "#859900",
}

# rebase: original naming for dark, renamed for light
DARK = {
    "03": COLOR["base03"],
    "02": COLOR["base02"],
    "01": COLOR["base01"],
    "00": COLOR["base00"],
    "0": COLOR["base0"],
    "1": COLOR["base1"],
    "2": COLOR["base2"],
    "3": COLOR["base3"],
}
LIGHT = {
    "03": COLOR["base3"],
    "02": COLOR["base2"],
    "01": COLOR["base1"],
    "00": COLOR["base0"],
    "0": COLOR["base00"],
    "1": COLOR["base01"],
    "2": COLOR["base02"],
    "3": COLOR["base03"],
}


def solarize(mode="dark"):
    """solarize(mode="dark")

    Changes default colors of matplotlib to solarized.

    Params
    ------
    mode: str
        Can be "light" or "dark". Defaults to "dark".

    """
    if mode == "dark":
        rebase = DARK
    elif mode == "light":
        rebase = LIGHT

    params = {
        "ytick.color": rebase["0"],  # 'k'
        "xtick.color": rebase["0"],  # 'k'
        "text.color": rebase["0"],  # 'k'
        "savefig.facecolor": rebase["03"],  # 'w'
        "patch.facecolor": COLOR["blue"],  # 'b'
        "patch.edgecolor": rebase["0"],  # 'k'
        "grid.color": rebase["0"],  # 'k'
        "figure.edgecolor": rebase["03"],  # 'w'
        "figure.facecolor": rebase["02"],  # '0.75'
        "axes.prop_cycle": cycler(
            "color",
            [
                COLOR["blue"],
                COLOR["green"],
                COLOR["red"],
                COLOR["cyan"],
                COLOR["magenta"],
                COLOR["yellow"],
                rebase["0"],
            ],
        ),
        # ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        "axes.edgecolor": rebase["0"],  # 'k'
        "axes.facecolor": rebase["03"],  # 'w'
        "axes.labelcolor": rebase["0"],  # 'k'
    }

    mpl.rcParams.update(params)


def dark():
    """dark()

    Changes default colors of matplotlib to solarized dark theme.

    """
    solarize()


def light():
    """dark()

    Changes default colors of matplotlib to solarized light theme.

    """
    solarize("light")


def gradient(num, colors="br"):
    """gradient(num, colors="br")

    Params
    ------
    num: number
        Indicates how many individual colors should be returned.
    colors: str
        A string of several char coded standard colors. "yormvbcg"

    Results
    -------
    out: ndarray (num, 3)
        Array of colors (RGB, values 0 to 1).

    """
    coldict = {}
    for color in [
        "yellow",
        "orange",
        "red",
        "magenta",
        "violet",
        "blue",
        "cyan",
        "green",
    ]:
        hex_str = COLOR[color][1:]
        hex_r = hex_str[:2]
        hex_g = hex_str[2:4]
        hex_b = hex_str[4:6]
        num_r = int(hex_r, 16) / 255.0
        num_g = int(hex_g, 16) / 255.0
        num_b = int(hex_b, 16) / 255.0
        coldict[color[0]] = np.array([num_r, num_g, num_b])

    blue = np.array([38, 139, 220]) / 255.0
    green = np.array([133, 153, 0]) / 255.0

    num_colors = len(colors)

    if num_colors > num:
        palette = np.empty((num, 3))
        for idx in range(num):
            palette[idx] = coldict[colors[idx]]

        return palette

    else:
        num_gradients = num_colors - 1
        num_part = (num - num_colors) % num_gradients
        num_all = (num - num_colors) // num_gradients
        fill_part = range(num_part)
        palettes = {"R": [], "G": [], "B": []}
        first = True
        for gdx in range(num_gradients):
            if first:
                c_f = 0
                first = False
            else:
                c_f = 1
            if gdx in fill_part:
                cur_num = num_all + 3
            else:
                cur_num = num_all + 2
            palettes["R"].append(
                np.linspace(
                    coldict[colors[gdx]][0], coldict[colors[gdx + 1]][0], cur_num
                )[c_f:]
            )
            palettes["G"].append(
                np.linspace(
                    coldict[colors[gdx]][1], coldict[colors[gdx + 1]][1], cur_num
                )[c_f:]
            )
            palettes["B"].append(
                np.linspace(
                    coldict[colors[gdx]][2], coldict[colors[gdx + 1]][2], cur_num
                )[c_f:]
            )
        palette = np.vstack(
            (
                np.concatenate(palettes["R"]),
                np.concatenate(palettes["G"]),
                np.concatenate(palettes["B"]),
            )
        ).T
        return palette


dark()
