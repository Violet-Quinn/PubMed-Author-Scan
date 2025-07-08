# Import necessary libraries
import typer  # Typer for CLI creation
import pandas as pd  # Pandas for tabular data handling
import logging  # Logging for debug/info messages
from typing import Optional  # Optional type hint for optional arguments
import requests  # HTTP requests for accessing PubMed API
import click  # Underlying CLI toolkit used by Typer
from .core import fetch_pubmed_ids, fetch_pubmed_details  # Custom functions for PubMed API interaction

# Create a Typer application instance
app = typer.Typer(
    pretty_exceptions_show_locals=False,  # Don't show local vars on crash
    add_completion=True,  # Enable shell completion
    help="CLI tool to fetch PubMed papers with non-academic (pharma/biotech) authors."
)


# Setup logging configuration
def setup_logging(debug: bool):
    """
    Configure the logging level and format based on debug flag.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')


# Custom callback to show help text for --help/-h before validation
def print_help_callback(ctx: click.Context, value: bool):
    """
    Display the help message and exit if --help or -h is passed.
    """
    if value:
        typer.echo(ctx.get_help())
        raise typer.Exit()


# Define the CLI command function (default command)
@app.command()
def main(
        # Hidden context needed for help callback
        ctx: typer.Context = typer.Option(None, hidden=True),

        # Required query string for PubMed search
        query: Optional[str] = typer.Argument(
            None,
            help="PubMed query (use quotes for complex queries)"
        ),

        # Optional output file name for saving results as CSV
        file: Optional[str] = typer.Option(
            None,
            "-f",
            "--file",
            help="Output CSV filename. If not provided, prints to console."
        ),

        # Optional debug flag for verbose logging
        debug: bool = typer.Option(
            False,
            "-d",
            "--debug",
            help="Enable debug output."
        ),

        # Help flag supporting both --help and -h using a callback
        show_help: Optional[bool] = typer.Option(
            None,
            "--help",
            "-h",
            is_eager=True,  # Execute this before any argument parsing
            help="Show this message and exit.",
            callback=print_help_callback  # Display help and exit
        )
):
    """
    Main command function.
    Fetch PubMed papers with at least one non-academic (pharma/biotech) author and output as CSV.
    """
    # If no query is given, print help and exit
    if query is None:
        typer.echo(typer.Context(app).get_help())
        raise typer.Exit()

    # Set up logging level
    setup_logging(debug)
    logging.info(f"Fetching PubMed IDs for query: {query}")

    try:
        # Step 1: Fetch PubMed IDs for the given query
        ids = fetch_pubmed_ids(query)
        logging.info(f"Found {len(ids)} PubMed IDs.")

        # Step 2: Fetch full paper metadata for the IDs
        papers = fetch_pubmed_details(ids)
        logging.info(f"Filtered to {len(papers)} papers with non-academic authors.")

        # Step 3: Handle empty result
        if not papers:
            typer.echo("No papers found with non-academic (pharma/biotech) authors.")
            raise typer.Exit(code=0)

        # Step 4: Convert results to DataFrame
        df = pd.DataFrame(papers)

        # Step 5: Output results to file or console
        if file:
            df.to_csv(file, index=False)
            typer.echo(f"Results saved to {file}")
        else:
            typer.echo(df.to_csv(index=False))

    # Handle HTTP errors from requests
    except requests.exceptions.HTTPError as e:
        typer.echo("\n[ERROR] HTTP error occurred while accessing an external API:", err=True)
        typer.echo(str(e), err=True)

    # Handle any other unexpected exceptions
    except Exception as e:
        typer.echo("\n[ERROR] An unexpected error occurred:", err=True)
        typer.echo(str(e), err=True)


# Entry point for running as a script: `python cli.py`
if __name__ == "__main__":
    app()


# Entry point for Poetry script: `poetry run get-papers-list`
def main():
    app()
