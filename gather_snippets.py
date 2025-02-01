from pathlib import Path
from agent import query
from db import save_to_db, check_file_already_processed, set_db_name

from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
import argparse

load_dotenv()

console = Console()


def process_directory(pdf_dir: str | Path, provider: str) -> None:
    """Process all PDF files in the given directory."""
    if isinstance(pdf_dir, str):
        pdf_dir = Path(pdf_dir)

    # Ensure directory exists
    if not pdf_dir.exists() or not pdf_dir.is_dir():
        console.print(f"[red]Invalid directory path:[/red] {pdf_dir}")
        raise ValueError(f"Invalid directory path: {pdf_dir}")

    # Get all PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        console.print(f"[yellow]No PDF files found in[/yellow] {pdf_dir}")
        return

    # Create a table to display file information
    table = Table(title="PDF Files Found", show_header=True, header_style="bold magenta")
    table.add_column("File Name", style="cyan")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Status", style="yellow")

    for pdf_file in pdf_files:
        status = "[red]Pending[/red]"
        if check_file_already_processed(pdf_file):
            status = "[blue]Already Processed[/blue]"
        table.add_row(pdf_file.name, f"{pdf_file.stat().st_size / 1024:.1f} KB", status)

    console.print(table)
    console.print(f"\n[green]Found[/green] {len(pdf_files)} PDF files")

    # Process each PDF file
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("Processing PDFs...", total=len(pdf_files))

        for pdf_file in pdf_files:
            if check_file_already_processed(pdf_file):
                console.print(
                    Panel(
                        f"Skipping [cyan]{pdf_file.name[:20]}...[/cyan] (already processed)",
                        border_style="yellow",
                        expand=False,
                    )
                )
                progress.advance(task)
                continue

            try:
                console.rule(f"[bold blue]Processing {pdf_file.name}")

                # Query the AI model
                response = query(pdf_file, provider=provider)

                # Save to database with source filename
                with console.status("[yellow]Saving to database...[/yellow]", spinner="dots"):
                    save_to_db(response, pdf_file.name)

                console.print(
                    f"[green]✓[/green] Successfully processed [blue]{pdf_file.name}[/blue]"
                )

            except Exception as e:
                console.print(f"[red]Error processing {pdf_file.name}:[/red] {str(e)}")
                continue

            finally:
                progress.advance(task)

        progress.update(task, completed=len(pdf_files))


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Process PDF files and save snippets to the database."
    )
    parser.add_argument(
        "-d",
        "--dir",
        type=str,
        default=".",
        help="Directory containing PDF files to process.",
    )
    parser.add_argument(
        "-n", "--db_name", type=str, help="Database name to use for the connection."
    )
    parser.add_argument(
        "-p",
        "--provider",
        type=str,
        choices=["qwen", "deepseek", "openai", "groq"],
        default="qwen",
        help="Provider to use for querying the AI model.",
    )
    args = parser.parse_args()

    # Display startup information
    startup_info = Table.grid(padding=1)
    startup_info.add_row("Directory:", f"[blue]{args.dir}[/blue]")
    startup_info.add_row("Provider:", f"[magenta]{args.provider}[/magenta]")
    if args.db_name:
        startup_info.add_row("Database:", f"[cyan]{args.db_name}[/cyan]")
        set_db_name(args.db_name)

    console.print(Panel(startup_info, title="PDF Processing Configuration", border_style="green"))

    try:
        process_directory(pdf_dir=args.dir, provider=args.provider)
        console.print("\n[green]Processing complete![/green]")
    except Exception as e:
        console.print(f"\n[red]Error during processing:[/red] {str(e)}")


if __name__ == "__main__":
    main()
