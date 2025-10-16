"""
Statistical helpers: sigma, Cp/Cpk, control limits, and safe text.
"""

from typing import Optional
import numpy as np

def sigma_to_risk(sigma: float) -> str:
    if not np.isfinite(sigma): return "N/A"
    if sigma < 3.0:  return "High risk"
    if sigma < 4.0:  return "Poor"
    if sigma < 4.5:  return "Moderate"
    if sigma < 5.0:  return "Acceptable"
    if sigma < 6.0:  return "Good"
    return "Excellent"

def safe_sigma_text(val: Optional[float]) -> str:
    if val is None: return "N/A"
    if not np.isfinite(val): return "inf"
    return f"{val:.3f}"
