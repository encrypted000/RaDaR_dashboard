from pathlib import Path
import pandas as pd

def project_root() -> Path:
    return Path(__file__).resolve().parents[1]

def module_dirs(module: str) -> dict[str, Path]:
    base = project_root() / "outputs" / module
    raw = base / "raw"
    reports = base / "reports"
    kpis = base / "kpis"

    raw.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    kpis.mkdir(parents=True, exist_ok=True)

    return {"base": base, "raw": raw, "reports": reports, "kpis": kpis}


def list_raw_snapshots(module: str) -> list[Path]:
    d = module_dirs(module)["raw"]
    files = list(d.glob(f"missing_{module}_*.csv"))
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)



def load_raw_snapshot(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"patient_id": "string"})

    if "recruited_date" in df.columns:
        df["recruited_date"] = pd.to_datetime(df["recruited_date"], errors="coerce")

    if "diagnosed_date" in df.columns:
        df["diagnosed_date"] = pd.to_datetime(df["diagnosed_date"], errors="coerce")

    return df


def load_weekly_kpis(module: str) -> pd.DataFrame:
    kpi_path = module_dirs(module)["kpis"] / "weekly_kpis.csv"
    if not kpi_path.exists():
        return pd.DataFrame(columns=[
        "week_monday",
        "missing_count",
        "new_missing",
        "still_missing",
        "resolved",
        "total_eligible",
        "uploaded",
        "completeness_percent",
        "adult_missing",
        "child_missing",
    ])
    return pd.read_csv(kpi_path, parse_dates=["week_monday"]).sort_values("week_monday")
