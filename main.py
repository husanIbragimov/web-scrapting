import asyncio
import logging
import pathlib
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

from config import SITES, DB_PATH, DEFAULT_MAX_PRODUCTS, LOG_PATH
from db.database import AsyncDatabase
from exporters.exporter import export

console = Console()


def _setup_logging() -> None:
    log_dir = pathlib.Path(LOG_PATH)
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"scrape_{timestamp}.log"

    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    logging.getLogger(__name__).info(f"Logging to {log_file}")


_setup_logging()


def prompt_sites() -> List[str]:
    console.print("\n[bold cyan]Available sites:[/bold cyan]")
    site_list = list(SITES.keys())
    for i, name in enumerate(site_list, 1):
        console.print(f"  {i}. {name}")
    console.print(f"  0. All sites")
    raw = Prompt.ask("Enter site numbers separated by commas (e.g. 1,3) or 0 for all")
    if raw.strip() == "0":
        return site_list
    chosen = []
    for part in raw.split(","):
        try:
            idx = int(part.strip()) - 1
            if 0 <= idx < len(site_list):
                chosen.append(site_list[idx])
        except ValueError:
            pass
    return chosen or site_list


async def main() -> None:
    console.rule("[bold green]E-Commerce Web Scraper[/bold green]")

    query = Prompt.ask("[bold]Search query[/bold] (e.g. 'wireless headphones')")
    chosen_sites = prompt_sites()
    max_products = IntPrompt.ask(
        f"Max products per site", default=DEFAULT_MAX_PRODUCTS
    )
    fmt = Prompt.ask("Output format", choices=["csv", "xlsx"], default="csv")

    console.print(f"\n[yellow]Starting scrape:[/yellow] '{query}' on {chosen_sites}")

    db = AsyncDatabase(DB_PATH)
    await db.init()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=200)
        tasks = []
        for site_name in chosen_sites:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="en-US",
            )
            scraper_cls = SITES[site_name]
            scraper = scraper_cls(context, query, max_products, db)
            tasks.append(asyncio.create_task(scraper.run(), name=site_name))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()

    # Aggregate and show results table
    table = Table(title="Scraping Results")
    table.add_column("Site", style="cyan")
    table.add_column("Products", justify="right", style="green")
    table.add_column("Status", style="yellow")

    for site_name, result in zip(chosen_sites, results):
        if isinstance(result, Exception):
            table.add_row(site_name, "0", f"ERROR: {result}")
        else:
            table.add_row(site_name, str(len(result)), "OK")

    console.print(table)

    all_rows = await db.get_all()
    if all_rows:
        out_path = export(all_rows, fmt, query)
        console.print(f"\n[bold green]Exported {len(all_rows)} products to:[/bold green] {out_path}")
    else:
        console.print("[red]No products collected.[/red]")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
