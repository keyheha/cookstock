import csv
import datetime as dt
import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cookStock import (  # noqa: E402
    SCREENER_CSV_HEADER,
    cookFinancials,
    sort_csv_by_buy_signal,
)


class VcpScreenerTests(unittest.TestCase):
    def make_stock(self, closes):
        stock = cookFinancials.__new__(cookFinancials)
        stock.ticker = "TEST"
        stock.m_recordVCP = []
        stock.m_footPrint = []
        stock.priceData = {
            "TEST": {
                "prices": [
                    {
                        "formatted_date": (
                            dt.date(2026, 1, 1) + dt.timedelta(days=i)
                        ).isoformat(),
                        "close": close,
                    }
                    for i, close in enumerate(closes)
                ]
            }
        }
        return stock

    def test_sma_uses_complete_trading_session_count(self):
        stock = self.make_stock([10, 20, 30, 40])

        self.assertEqual(stock._get_session_sma(dt.date(2026, 1, 4), 3), 30.0)
        self.assertEqual(stock._get_session_sma(dt.date(2026, 1, 4), 5), -1)

    def test_vcp_search_advances_beyond_the_previous_low(self):
        stock = self.make_stock([])
        calls = []

        def find_one(start_date):
            calls.append(start_date)
            return True, "2026-01-02", 100, "2026-01-03", 90

        stock.find_one_contraction = find_one
        count, contractions = stock.find_volatility_contraction_pattern(
            dt.date(2026, 1, 1)
        )

        self.assertEqual(count, 1)
        self.assertEqual(len(contractions), 1)
        self.assertEqual(calls[:2], [dt.date(2026, 1, 1), dt.date(2026, 1, 4)])

    def test_volume_trend_handles_short_or_invalid_windows(self):
        stock = self.make_stock([])

        self.assertEqual(stock._calculate_volume_trend([]), (0.0, 0.0))
        self.assertEqual(stock._calculate_volume_trend([125]), (0.0, 125.0))
        self.assertEqual(stock._calculate_volume_trend([1, float("nan")]), (0.0, 0.0))

    def test_csv_sort_uses_column_names_after_schema_changes(self):
        def row(ticker, pressure, distance):
            values = {name: "NO" for name in SCREENER_CSV_HEADER}
            values.update(
                {
                    "Ticker": ticker,
                    "VCP Buy": "YES",
                    "VCP Changed": "NO",
                    "Pressure Price": str(pressure),
                    "Price to Support %": str(distance),
                }
            )
            return [values[name] for name in SCREENER_CSV_HEADER]

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen.csv")
            with open(path, "w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(SCREENER_CSV_HEADER)
                writer.writerow(row("FAR", 1, 10))
                writer.writerow(row("NEAR", 999, 2))

            sort_csv_by_buy_signal(path)

            with open(path, newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([item["Ticker"] for item in rows], ["NEAR", "FAR"])


if __name__ == "__main__":
    unittest.main()
