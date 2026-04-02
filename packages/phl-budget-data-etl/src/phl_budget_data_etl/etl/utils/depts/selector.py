"""Module for interactively selecting a department match."""

from __future__ import annotations

import questionary


def launch_selector(options: list[str], value: str, results_per_page: int = 10) -> str | None:
    """
    Interactively select the best match for an unrecognized department name.

    Uses questionary.autocomplete so the user can type to filter the list.
    Returns None if the user cancels (Ctrl-C / empty selection).
    """
    print(f"\nNo match found for department: '{value}'")
    result = questionary.autocomplete(
        "Select the correct department:",
        choices=options,
        validate=lambda x: x in options or "Please select a valid option",
    ).ask()
    return result if result else None
