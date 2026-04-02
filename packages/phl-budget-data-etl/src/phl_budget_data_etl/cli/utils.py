"""Utilities module for command-line interface."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from phl_budget_data import DATA_DIR


def determine_file_name(f: Callable[..., Any], **kwargs: Any) -> Path:
    """Given a function, determine the matching file name."""
    # The parts
    name = f.__name__
    tag = f.__module__.split(".")[-1]

    # The base of the file name
    filename_base = "-".join(name.split("_")[1:])

    # The output folder
    output_folder = DATA_DIR / "historical" / tag

    # Function has required params
    if hasattr(f, "model"):
        # Get the params
        schema = f.model.model_json_schema()

        # Do all iterations of params
        param_values: list[str] = [kwargs.get(k, "") for k in schema["required"]]

        # If any are missing raise an error
        if any(value == "" for value in param_values):
            raise ValueError("Missing required params")

        # The filename
        filename = filename_base + "-" + "-".join(param_values) + ".csv"
        output_file = output_folder / filename
    else:
        filename = "-".join(name.split("_")[1:]) + ".csv"
        output_file = output_folder / filename

    return output_file
