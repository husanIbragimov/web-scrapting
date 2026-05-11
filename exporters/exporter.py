import pathlib
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

def generate_filename(query: str, fmt: str, output_dir: pathlib.Path = None) -> pathlib.Path:
    if output_dir is None:
        output_dir = pathlib.Path("output")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return output_dir / f"products_{timestamp}.{fmt}"

def export(
    rows: List[Dict[str, Any]],
    fmt: str,
    query: str,
    output_dir: pathlib.Path = None,
) -> pathlib.Path:
    """Export rows to CSV or Excel. Returns the path of the created file."""
    if output_dir is None:
        output_dir = pathlib.Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)
    path = generate_filename(query, fmt, output_dir)

    if fmt == "csv":
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif fmt == "xlsx":
        df.to_excel(path, index=False, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported format: {fmt}. Use 'csv' or 'xlsx'.")

    return path
