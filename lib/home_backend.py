from datetime import datetime
from pathlib import Path

import pandas as pd

from lib.db import get_connection
from lib.queries import (
    SQL_REGISTRY_OVERVIEW,
    SQL_TOTAL_COHORTS,
    SQL_HOME_COHORT_STRUCTURE,
)


# =============================================================================
# PATHS
# =============================================================================

def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def output_dir() -> Path:
    path = project_root() / "outputs" / "home"
    path.mkdir(parents=True, exist_ok=True)
    return path


# =============================================================================
# HELPERS
# =============================================================================

def run_query(sql: str, conn, label: str) -> pd.DataFrame:
    """Run a SQL query and return a DataFrame. Raises with a clear message on failure."""
    try:
        df = pd.read_sql(sql, conn)
        print(f"  ✓ Query OK [{label}] — {len(df)} row(s) returned")
        return df
    except Exception as e:
        raise RuntimeError(f"Query failed [{label}]: {e}") from e


def safe_int(row, *keys) -> int | None:
    """Try multiple column name variants and return the first that exists as an int."""
    for key in keys:
        if key in row and pd.notna(row[key]):
            try:
                return int(row[key])
            except (ValueError, TypeError):
                continue
    return None


# =============================================================================
# PIPELINE
# =============================================================================

def run_backend():

    home_dir = output_dir()
    conn, tunnel = get_connection()

    try:
        registry_df       = run_query(SQL_REGISTRY_OVERVIEW,     conn, "registry_overview")
        cohort_df         = run_query(SQL_TOTAL_COHORTS,          conn, "total_cohorts")
        cohort_structure_df = run_query(SQL_HOME_COHORT_STRUCTURE, conn, "cohort_structure")
    finally:
        conn.close()
        tunnel.stop()

    if registry_df.empty:
        print("  ⚠  registry_overview query returned no rows — skipping save")
        total_patients = male_patients = female_patients = unknown_sex = None
    else:
        row = registry_df.iloc[0]
        total_patients  = safe_int(row, "total_patients",  "total")
        male_patients   = safe_int(row, "male_patients",   "male_count",   "males")
        female_patients = safe_int(row, "female_patients", "female_count", "females")
        unknown_sex     = safe_int(row, "unknown_gender",  "unknown_sex",  "unknown")

        if male_patients is None:
            print(f"  ⚠  Could not find male count — columns available: {list(registry_df.columns)}")
        if female_patients is None:
            print(f"  ⚠  Could not find female count — columns available: {list(registry_df.columns)}")
        if unknown_sex:
            print(f"  ℹ  {unknown_sex} patients have sex not recorded (gender ≠ 1/2)")

    if cohort_df.empty:
        print("  ⚠  total_cohorts query returned no rows — defaulting to 0")
        total_cohorts = 0
    else:
        total_cohorts = safe_int(cohort_df.iloc[0], "total_cohorts", "cohort_count", "count")
        if total_cohorts is None:
            print(f"  ⚠  Could not find cohort count — columns available: {list(cohort_df.columns)}")
            total_cohorts = 0

    registry_result = pd.DataFrame([{
        "total_patients":  total_patients,
        "male_patients":   male_patients,
        "female_patients": female_patients,
        "unknown_sex":     unknown_sex,
        "total_cohorts":   total_cohorts,
        "run_timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M"),
    }])
    registry_result.to_csv(home_dir / "registry_overview.csv", index=False)

    EXPECTED_COHORT_COLS = {"name", "adult_count", "child_count", "total_patients"}
    actual_cols = set(cohort_structure_df.columns)
    missing_cols = EXPECTED_COHORT_COLS - actual_cols

    if missing_cols:
        print(f"  ⚠  cohort_structure is missing expected columns: {missing_cols}")
        print(f"     Columns actually returned: {list(actual_cols)}")
        print("     Saving anyway — home page cohort table may be incomplete")
    
    if cohort_structure_df.empty:
        print("  ⚠  cohort_structure query returned no rows")

    cohort_structure_df.to_csv(home_dir / "cohort_structure.csv", index=False)

    print("=" * 50)
    print(f"  Total patients  : {total_patients}")
    print(f"  Male patients   : {male_patients}")
    print(f"  Female patients : {female_patients}")
    print(f"  Total cohorts   : {total_cohorts}")
    print(f"  Cohort rows     : {len(cohort_structure_df)}")
    print(f"  Run timestamp   : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    print("Saved:", home_dir / "registry_overview.csv")
    print("Saved:", home_dir / "cohort_structure.csv")
