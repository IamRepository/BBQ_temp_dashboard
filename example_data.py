from __future__ import annotations

import uuid
import pandas as pd
from models import CookProfile


def load_example_profiles():
    examples = [
        ("Competition brisket", "Point", "#f97316", [8,31,49,62,68,72,75,81,88,93,91,88,84,80,78,76,74,72,70,69]),
        ("Long hold test", "Flat", "#38bdf8", [10,28,45,58,64,67,70,76,83,89,92,90,86,83,81,78,77,76,75,74]),
        ("Hot and fast", "Flat", "#a78bfa", [9,39,61,70,77,85,92,90,84,79,76,74,73,71,70,69,68,67,65,64]),
    ]
    result = []
    for name, channel, color, temperatures in examples:
        data = pd.DataFrame({"elapsed_hours": list(range(len(temperatures))), "temperature_c": temperatures})
        result.append(CookProfile(uuid.uuid4().hex, name, "built-in example", channel, color, data))
    return result
