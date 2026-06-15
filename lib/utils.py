import pandas as pd

SCHWARTZ_K = 36.5  # k constant for creatinine in μmol/L, height in cm


def schwartz_egfr(height: pd.Series, creatinine: pd.Series) -> pd.Series:
    """Schwartz eGFR (mL/min/1.73m²) = 36.5 × height(cm) ÷ creatinine(μmol/L)."""
    safe_cr = creatinine.where(creatinine > 0)
    return (SCHWARTZ_K * height / safe_cr).round(1)
