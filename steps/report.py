"""Revenue by region and month (revenue_by_region_month.csv)."""

import os

import pandas as pd

DATA = os.environ.get("DATA", os.path.expanduser("~/data/sales_2025.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/data/out"))
os.makedirs(OUT, exist_ok=True)

# Fixed with Claude Code (Anthropic, Claude Sonnet 5.5); prompt: "help me do them".
# Read only the four columns we use, and parse the dates while reading, so
# the 8.4 million date strings never exist as Python objects.
orders = pd.read_csv(DATA, usecols=["order_date", "region", "quantity", "unit_price"],
                     parse_dates=["order_date"],
                     dtype={"region": "category", "quantity": "int16"})
size = orders.memory_usage(deep=True).sum() / 2**20
print(f"report: loaded {len(orders):,} orders ({size:.0f} MiB)", flush=True)

orders["revenue"] = orders["quantity"] * orders["unit_price"]

# Group the table directly: no per-month copies of the data, no concat.
table = orders.groupby(["region", orders["order_date"].dt.month], observed=True)["revenue"].sum().unstack()
table.round(2).to_csv(os.path.join(OUT, "revenue_by_region_month.csv"))
print("report: done")
