"""
Incremental source connector (cloud ingestion path).

Illustrates the watermark/CDC pattern used to pull only-new records from CTMS-style OData/REST
sources (and marketing Lead Ads / financial APIs) and land them in ADLS for the Bronze layer.
In Azure this runs inside an ADF-orchestrated Databricks/Functions task; the watermark store is a
small Delta/SQL table. Kept dependency-free so it documents the pattern clearly.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass
class WatermarkStore:
    """Persists the last-seen high-water-mark per source (Delta table dtbi.silver._load_watermark)."""
    state: dict

    def get(self, source: str) -> datetime:
        return self.state.get(source, datetime(1900, 1, 1))

    def set(self, source: str, value: datetime) -> None:
        self.state[source] = value


class IncrementalExtractor:
    """Pulls records modified after the stored watermark, then advances it on success."""

    def __init__(self, source_name: str, watermark_col: str, store: WatermarkStore):
        self.source_name = source_name
        self.watermark_col = watermark_col
        self.store = store

    def build_query(self) -> dict:
        last = self.store.get(self.source_name)
        # e.g. OData: $filter=ModifiedOn gt 2026-05-01T00:00:00Z
        return {"$filter": f"{self.watermark_col} gt {last.isoformat()}Z",
                "$orderby": f"{self.watermark_col} asc"}

    def run(self, fetch_page) -> int:
        """fetch_page(query) -> iterable of records. Returns number of rows landed."""
        query = self.build_query()
        rows, max_wm = 0, self.store.get(self.source_name)
        for record in fetch_page(query):
            rows += 1
            wm = record.get(self.watermark_col)
            if wm and wm > max_wm:
                max_wm = wm
            self._land(record)
        if rows:
            self.store.set(self.source_name, max_wm)  # advance only after a clean pass (idempotent)
        return rows

    def _land(self, record: dict) -> None:
        # In Azure: append to abfss://landing@.../<source>/. Here it is a no-op stub.
        pass


def example():
    store = WatermarkStore(state={})
    extractor = IncrementalExtractor("ctms_enrollment", "ModifiedOn", store)
    sample = [{"patient_id": "PT-1", "ModifiedOn": datetime(2026, 5, 2)}]
    landed = extractor.run(lambda q: iter(sample))
    print(f"landed {landed} rows; new watermark = {store.get('ctms_enrollment')}")


if __name__ == "__main__":
    example()
