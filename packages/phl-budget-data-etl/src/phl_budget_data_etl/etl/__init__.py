"""Main module for data ETL (development version only)."""

from pathlib import Path
from typing import Literal

ETL_DATA_DIR = Path(__file__).parent.parent / "data"
ETL_DATA_FOLDERS = Literal["raw", "processed", "interim"]
