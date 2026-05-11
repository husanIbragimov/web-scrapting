import pytest
import pathlib
import pandas as pd
from exporters.exporter import export, generate_filename

def test_generate_filename_csv():
    path = generate_filename("laptop", "csv")
    assert path.suffix == ".csv"
    assert "products_" in path.name
    assert path.parent.name == "output"

def test_generate_filename_xlsx():
    path = generate_filename("shoes", "xlsx")
    assert path.suffix == ".xlsx"

def test_export_csv_creates_file(tmp_path):
    rows = [
        {"url": "https://a.com/1", "source_site": "amazon", "name": "Laptop", "price": 999.0, "currency": "USD"},
        {"url": "https://a.com/2", "source_site": "ebay",   "name": "Phone",  "price": 499.0, "currency": "USD"},
    ]
    out_path = export(rows, "csv", "laptop", tmp_path / "output")
    assert out_path.exists()
    df = pd.read_csv(out_path)
    assert len(df) == 2
    assert "name" in df.columns

def test_export_xlsx_creates_file(tmp_path):
    rows = [{"url": "https://a.com/1", "source_site": "amazon", "name": "TV", "price": 1200.0}]
    out_path = export(rows, "xlsx", "tv", tmp_path / "output")
    assert out_path.exists()
    df = pd.read_excel(out_path)
    assert len(df) == 1
