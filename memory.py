"""
JSON‑backed cross‑week memory for I‑MR accumulation and cleanup.
"""

import json
import os
from typing import Dict, List, Any, Tuple, Optional

Record = Dict[str, Any]

"""
SPC Memory Rules (I-MR only)
If the current week has fewer than 20 points: load all historical data + current data.
If the total is still fewer than 20 points: save only the current data into memory, and do not generate a chart for this week.
If the total is 20 points or more: use (historical + current data) to generate the chart, and then clear the memory for that feature.

Notes:
Control limits (LSL/USL/LCL/UCL) always come from the current week’s file.
I-MR memory only accumulates single-point values.
Memory keys follow the format "<product>|<feature>", and different products/features are independent of each other.
"""

class MemoryStore:
    """
    JSON-backed memory keyed by "<product>|<feature>".

    I-MR single point record:
    {"type":"IMR","week":"YYYYMMDD-YYYYMMDD","id":"first column","value":float}
    """
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.data: Dict[str, List[Record]] = {}
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        tmp = self.json_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.json_path)

    @staticmethod
    def _key(product: str, feature: str) -> str:
        return f"{product}|{feature}"

    # ---------- IMR ----------
    def add_imr_points(
        self,
        product: str,
        feature: str,
        week: str,
        ids: List[Any],
        values: List[float],
    ) -> None:
        """Add current week's IMR points into memory; deduplicate by (week, id)."""
        key = self._key(product, feature)
        bucket = self.data.setdefault(key, [])
        seen = {(r.get("week"), str(r.get("id"))) for r in bucket if r.get("type") == "IMR"}
        for i, v in zip(ids, values):
            tag = (week, str(i))
            if tag not in seen:
                bucket.append({"type": "IMR", "week": week, "id": str(i), "value": float(v)})
        # Order by type, then week, then numeric id (avoid "1,10,11,2" string-order issue)
        bucket.sort(key=lambda r: (r.get("type", ""), r.get("week", ""), int(r.get("id", 0))))
        self._save()

    def take_imr_until(
        self,
        product: str,
        feature: str,
        need: Optional[int],
        exclude_week: Optional[str] = None,
    ) -> Tuple[List[str], List[float]]:
        """
        Take IMR historical points from the oldest.
        - If 'need' is None: take ALL historical points (except exclude_week).
        - Else: take up to 'need' points.
        Returns (weeks_used_in_order, values_oldest_first); does not delete original data.
        """
        key = self._key(product, feature)
        weeks: List[str] = []
        vals: List[float] = []
        for r in self.data.get(key, []):
            if r.get("type") != "IMR":
                continue
            if exclude_week and r.get("week") == exclude_week:
                continue
            weeks.append(r["week"])
            vals.append(float(r["value"]))
            if need is not None and len(vals) >= need:
                break
        return weeks, vals

    # ---------- Clear ----------
    def clear_feature(self, product: str, feature: str) -> None:
        """Clear all memory records for the given product|feature key."""
        key = self._key(product, feature)
        if key in self.data:
            del self.data[key]
            self._save()