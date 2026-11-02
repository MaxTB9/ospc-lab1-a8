#!/bin/bash
# One file per region for the regional managers, with the columns
# order_id, order_date, product_category, quantity, unit_price.
set -euo pipefail

DATA=${DATA:-$HOME/data/sales_2025.csv}
DATA=$(realpath "$DATA")
OUT=${OUT:-$HOME/data/out}
mkdir -p "$OUT/extracts"
cd "$OUT/extracts"
for region in Iberia DACH France Italy Benelux Nordics; do
    grep ",$region," "$DATA" | cut -d, -f1,2,4,6,7 > "$region.csv"
done
echo "extracts: done"
