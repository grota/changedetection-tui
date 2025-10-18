from textual.theme import BUILTIN_THEMES
from copy import copy

changedetection_tui = copy(BUILTIN_THEMES["textual-dark"])
changedetection_tui.background = "#000000"
changedetection_tui.name = "changedetection_tui"
