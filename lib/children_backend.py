from datetime import datetime
from pathlib import Path

import pandas as pd

from lib.db import get_connection
from lib.queries import SQL_CHILDREN_COMPLETENESS

MODULE  = "children"
METRICS = ["height", "weight", "acr", "pcr", "diastolic_bp", "systolic_bp", "creatinine", "egfr"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def module_dirs() -> dict[str, Path]:
    base = project_root() / "outputs" / MODULE
    raw  = base / "raw"
    kpis = base / "kpis"
    raw.mkdir(parents=True, exist_ok=True)
    kpis.mkdir(parents=True, exist_ok=True)
    return {"base": base, "raw": raw, "kpis": kpis}


def metric_pct(df: pd.DataFrame, col: str) -> float:
    eligible = df[col].dropna()
    if eligible.empty:
        return 0.0
    return round(float(eligible.sum()) / len(eligible) * 100, 1)


def update_weekly_kpis(kpis_dir: Path, row_data: dict) -> None:
    kpi_path = kpis_dir / "weekly_kpis.csv"
    run_date = row_data["run_date"]
    row = pd.DataFrame([row_data])

    if kpi_path.exists():
        existing = pd.read_csv(kpi_path)
        existing = existing[existing["run_date"] != run_date]
        combined = pd.concat([existing, row], ignore_index=True)
        combined.to_csv(kpi_path, index=False)
    else:
        row.to_csv(kpi_path, index=False)


def run_backend():
    dirs = module_dirs()

    conn, tunnel = get_connection()
    try:
        df = pd.read_sql(SQL_CHILDREN_COMPLETENESS, conn)
    finally:
        conn.close()
        tunnel.stop()

    df["patient_id"] = df["patient_id"].astype(str)
    df["obs_year"]   = pd.to_numeric(df["obs_year"], errors="coerce")

    runstamp  = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snap_path = dirs["raw"] / f"children_completeness_{runstamp}.csv"
    df.to_csv(snap_path, index=False)

    total_children = int(df["patient_id"].nunique())
    total_sites    = int(df["hospital_name"].dropna().nunique())

    kpi_row: dict = {
        "run_date":       datetime.now().strftime("%Y-%m-%d"),
        "total_children": total_children,
        "total_sites":    total_sites,
    }

    pcts = []
    for m in METRICS:
        if m in df.columns:
            pct = metric_pct(df, m)
            kpi_row[f"{m}_pct"] = pct
            pcts.append(pct)

    kpi_row["overall_pct"] = round(sum(pcts) / len(pcts), 1) if pcts else 0.0

    update_weekly_kpis(dirs["kpis"], kpi_row)

    # Keep only 12 most recent snapshots
    snaps = sorted(dirs["raw"].glob("children_completeness_*.csv"), reverse=True)
    for old in snaps[12:]:
        old.unlink()

    print("=" * 50)
    print(f"  Total children  : {total_children}")
    print(f"  Total sites     : {total_sites}")
    for m in METRICS:
        key = f"{m}_pct"
        if key in kpi_row:
            print(f"  {m:<20}: {kpi_row[key]:.1f}%")
    print(f"  {'overall':<20}: {kpi_row['overall_pct']:.1f}%")
    print("=" * 50)
    print("Saved:", snap_path)
    print("Updated KPI:", dirs["kpis"] / "weekly_kpis.csv")
