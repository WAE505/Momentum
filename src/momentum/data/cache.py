"""Local caching for market data."""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from .sources import fetch_all_data


class DataCache:
    """SQLite-based cache for market data."""

    def __init__(self, db_path: str | Path = "data/market_data.db"):
        """
        Initialize the data cache.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    date TEXT PRIMARY KEY,
                    equity REAL,
                    bond REAL,
                    gold REAL,
                    cash REAL,
                    cash_rate REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def get_last_update(self) -> Optional[datetime]:
        """Get the timestamp of the last data update."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM metadata WHERE key = 'last_update'"
            )
            row = cursor.fetchone()
            if row:
                return datetime.fromisoformat(row[0])
            return None

    def _set_last_update(self, timestamp: datetime):
        """Set the timestamp of the last data update."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_update', ?)",
                (timestamp.isoformat(),)
            )
            conn.commit()

    def get_data(
        self,
        start_date: str = "1988-01-01",
        end_date: Optional[str] = None,
        max_cache_age_days: int = 1
    ) -> pd.DataFrame:
        """
        Get market data, fetching fresh data if cache is stale.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            max_cache_age_days: Maximum age of cache before refreshing

        Returns:
            DataFrame with market data
        """
        last_update = self.get_last_update()
        cache_is_fresh = (
            last_update is not None and
            datetime.now() - last_update < timedelta(days=max_cache_age_days)
        )

        if cache_is_fresh:
            # Load from cache
            df = self._load_from_cache()
            if not df.empty:
                # Filter by date range
                df["date"] = pd.to_datetime(df["date"])
                mask = df["date"] >= start_date
                if end_date:
                    mask &= df["date"] <= end_date
                return df[mask].reset_index(drop=True)

        # Fetch fresh data
        df = self.refresh_data(start_date, end_date)
        return df

    def _load_from_cache(self) -> pd.DataFrame:
        """Load all data from cache."""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM market_data ORDER BY date", conn)
        return df

    def refresh_data(
        self,
        start_date: str = "1988-01-01",
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch fresh data and update cache.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)

        Returns:
            DataFrame with fresh market data
        """
        # Fetch fresh data
        df = fetch_all_data(start_date, end_date)

        # Save to cache
        self._save_to_cache(df)
        self._set_last_update(datetime.now())

        return df

    def _save_to_cache(self, df: pd.DataFrame):
        """Save data to cache, replacing existing data."""
        # Convert date to string for SQLite
        df_to_save = df.copy()
        df_to_save["date"] = df_to_save["date"].astype(str)

        with sqlite3.connect(self.db_path) as conn:
            # Clear existing data
            conn.execute("DELETE FROM market_data")

            # Insert new data
            df_to_save.to_sql("market_data", conn, if_exists="append", index=False)
            conn.commit()

    def clear_cache(self):
        """Clear all cached data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM market_data")
            conn.execute("DELETE FROM metadata")
            conn.commit()
