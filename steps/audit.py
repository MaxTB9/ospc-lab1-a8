"""Audit trail: one line per order with its revenue (audit_2025.csv)."""

import os

import pandas as pd

DATA = os.environ.get("DATA", os.path.expanduser("~/data/sales_2025.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/data/out"))
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "audit_2025.csv")

orders = pd.read_csv(DATA, usecols=["order_id", "region", "quantity", "unit_price"])
orders["revenue"] = orders["quantity"] * orders["unit_price"]

# Fixed with Claude Code (Anthropic, Claude Sonnet 5.5); prompt: "help me do them".
# Open the file once. Python collects the lines in a 128 KiB buffer and calls
# write() once per full buffer, instead of one open/write/close per order.
# (Closing the file per order did not put the line on the disk either: the
# kernel keeps written data in its page cache until it chooses to flush it.)
with open(path, "w") as f:
    for order in orders.itertuples(index=False):
        f.write(f"{order.order_id},{order.region},{order.revenue:.2f}\n")
print(f"audit: {len(orders):,} lines written")
