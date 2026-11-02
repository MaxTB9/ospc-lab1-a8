"""Number of orders per region, quarter and order size (segments.csv)."""

import os

import numpy as np
import pandas as pd

DATA = os.environ.get("DATA", os.path.expanduser("~/data/sales_2025.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/data/out"))
os.makedirs(OUT, exist_ok=True)

orders = pd.read_csv(DATA, usecols=["order_date", "region", "quantity", "unit_price"],
                     dtype={"region": "category", "quantity": "int16"})

# Fixed with Claude Code (Anthropic, Claude Sonnet 5.5); prompt: "help me do them".
# One operation on whole columns instead of a Python function called once
# per order (8.4 million calls, each with a strptime).
month = orders["order_date"].str[5:7].astype("int8").to_numpy()
quarter = (month - 1) // 3 + 1
value = (orders["quantity"] * orders["unit_price"]).to_numpy()
size = np.select([value >= 500, value >= 100], [2, 1], default=0)

counts = orders.groupby(["region", quarter, size], observed=True).size().reset_index()
counts.columns = ["region", "quarter", "size", "orders"]
counts["segment"] = "Q" + counts["quarter"].astype(str) + " " + counts["size"].map(
    {2: "large", 1: "medium", 0: "small"})

table = counts.set_index(["region", "segment"])["orders"].unstack(fill_value=0)
table.to_csv(os.path.join(OUT, "segments.csv"))
print("segments: done")
