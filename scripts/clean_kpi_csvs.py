"""
Run this once from your project root to clean weekly_kpis.csv for both modules.
It removes blank rows and sorts by week_monday.
"""
from pathlib import Path
import pandas as pd

for module in ["biopsy", "genetics", "diagnoses"]:
    path = Path("outputs") / module / "kpis" / "weekly_kpis.csv"
    if not path.exists():
        print(f"Not found: {path}")
        continue

    df = pd.read_csv(path)

    before = len(df)

    # Remove fully blank rows
    df = df.dropna(how="all")

    # Remove rows where week_monday is blank
    df = df[df["week_monday"].notna() & (df["week_monday"].astype(str).str.strip() != "")]

    # Sort chronologically
    df["week_monday"] = pd.to_datetime(df["week_monday"], errors="coerce")
    df = df.dropna(subset=["week_monday"])
    df = df.sort_values("week_monday").reset_index(drop=True)
    df["week_monday"] = df["week_monday"].dt.strftime("%Y-%m-%d")

    after = len(df)

    df.to_csv(path, index=False)
    print(f"[{module}] {before} rows → {after} rows after clean")
    print(df.to_string())
    print()

