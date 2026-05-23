"""Ensure the local pipeline has produced Gold before tests run (keeps CI self-contained)."""
import subprocess, sys
import duckdb, pytest
from src.common.config import GOLD


@pytest.fixture(scope="session")
def gold():
    if not (GOLD / "kpi_overview.parquet").exists():
        subprocess.run([sys.executable, "-m", "src.generators.generate_all"], check=True)
        subprocess.run([sys.executable, "-m", "src.pipelines.local_run"], check=True)
    con = duckdb.connect()
    con.execute(f"SET file_search_path='{GOLD}'")

    def tbl(name):
        return con.execute(f"SELECT * FROM read_parquet('{GOLD / (name + '.parquet')}')").df()
    yield tbl
    con.close()
