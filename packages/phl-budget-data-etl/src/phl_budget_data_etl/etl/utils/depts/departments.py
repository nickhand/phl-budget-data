"""Department metadata for the City of Philadelphia (inlined from billy-penn)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel

DATA_DIR = Path(__file__).parent.resolve() / "data"


class Department(BaseModel):
    """
    An object representing a City of Philadelphia department.

    Parameters
    ----------
    name : str
        the name of the department
    dept_code : str
        the number of the department
    abbreviation : str, optional
        The department abbreviation
    """

    name: str
    dept_code: str
    abbreviation: str | None = None

    def __repr__(self) -> str:
        return f"<Department: {self.name}>"

    def __str__(self) -> str:
        return self.name


def load_city_departments(
    include_line_items: bool = False, include_aliases: bool = False
) -> pd.DataFrame:
    """Load City departments."""
    depts = []
    with (DATA_DIR / "depts.json").open("r") as ff:
        data = json.load(ff)
    for d in data:
        # Pop the line items
        line_items = d.pop("line-items") if "line-items" in d else None

        # Add the main department
        depts.append(Department(**d))

        # Add the line items
        if include_line_items and line_items is not None:
            for line_item in line_items:
                depts.append(Department(**line_item))

    # Create the dataframe
    out = (
        pd.DataFrame([dict(dept) for dept in depts])
        .replace(to_replace=[None], value=np.nan)
        .drop_duplicates(subset=["dept_code"])
    )

    assert out["dept_code"].duplicated().sum() == 0

    # Add aliases
    if include_aliases:
        # Get alias lookup
        lookup = pd.read_excel(DATA_DIR / "dept_names_lookup.xlsx", dtype=str)[
            ["dept_name", "dept_code"]
        ].drop_duplicates()

        aliases_column = []
        for _, row in out.iterrows():
            # Get lookup match
            matches = lookup.query(f"dept_code == '{row['dept_code']}'")
            aliases = []
            if len(matches):
                aliases = matches["dept_name"].tolist()
                if row["name"] not in aliases:
                    aliases.append(row["name"])
                if row["abbreviation"] not in aliases:
                    aliases.append(row["abbreviation"])

            aliases_column.append(aliases)

        out["aliases"] = aliases_column
        out = (
            out.join(out["aliases"].explode().rename("alias"))
            .drop(columns=["aliases"])
            .reset_index(drop=True)
            .assign(alias=lambda df: df["alias"].fillna(df["name"]))
            .drop_duplicates()
        )

    return out.rename(columns={"name": "dept_name"})
