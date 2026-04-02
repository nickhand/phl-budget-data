"""The main command-line interface for phl-budget-data."""

import importlib
import itertools
from pathlib import Path

import click
import typer
from loguru import logger
from phl_budget_data import DATA_DIR
from typer.main import get_group

from .etl import generate_commands as generate_etl_commands
from .update import generate_commands as generate_update_commands
from .utils import determine_file_name

app = typer.Typer(
    name="phl-budget-data",
    help="Main command-line interface for working with City of Philadelphia budget data.",
    no_args_is_help=True,
)


@app.command()
def save(
    output: str | None = typer.Option(None, help="The output folder."),
    save_sql: bool = typer.Option(False, "--save-sql", help="Whether to save SQL databases."),
) -> None:
    """Save the processed data products."""
    # Determine the output path
    output_path = Path(output) if output else DATA_DIR

    # Loop over each tag
    for tag in ["spending", "qcmr", "collections"]:
        # Handle output folder
        output_folder = output_path / tag
        output_folder.mkdir(parents=True, exist_ok=True)

        # Get the module
        mod = importlib.import_module(f"phl_budget_data_etl.etl.{tag}.processed")

        # Loop over each data loader
        for name in dir(mod):
            if name.startswith("load"):
                # The function
                f = getattr(mod, name)

                # Function has required params
                if hasattr(f, "model"):
                    # Get the params
                    schema = f.model.model_json_schema()
                    params = {k: schema["properties"][k]["enum"] for k in schema["required"]}

                    # Do all iterations of params
                    for param_values in list(itertools.product(*params.values())):
                        kwargs = dict(zip(schema["required"], param_values, strict=False))
                        data = f(**kwargs)

                        # The filename
                        filename = determine_file_name(f, **kwargs).name
                        output_file = output_folder / filename
                        logger.info(f"Saving {output_file}")
                        data.to_csv(output_file, index=False)
                # Function does not have required params
                else:
                    filename = determine_file_name(f).name
                    output_file = output_folder / filename
                    logger.info(f"Saving {output_file}")
                    f().to_csv(output_file, index=False)


# Build the top-level click group from the typer app (captures 'save').
# Then add 'etl' and 'update' as plain click.Groups so that commands
# registered via generate_*_commands() are on the same object that runs.
_cli = get_group(app)

_etl_group = click.Group("etl", help="Run the ETL pipeline for the specified data source.")
_update_group = click.Group(
    "update",
    help="Parse the City's website to scrape and update City of Philadelphia budget data.",
)

generate_etl_commands(_etl_group)
generate_update_commands(_update_group)

_cli.add_command(_etl_group)
_cli.add_command(_update_group)


def main() -> None:
    """Entry point."""
    _cli()
