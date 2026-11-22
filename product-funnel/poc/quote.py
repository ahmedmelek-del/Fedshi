"""Price a buyer quotation: python3 quote.py <item-id> <factory USD per unit> [more USD ...]

Example: python3 quote.py dent-puller 1.8 2.4
"""
import csv
import sys

from score import ASSUMPTIONS, price_for

rows = {r['id']: r for r in csv.DictReader(open('out/ranked.csv'))}
item = rows[sys.argv[1]]
freight = float(item['freight_iqd'])
print(f"{item['name']} | billed {item['bill_kg']} kg | air {freight:,.0f} IQD ({item['freight_type']})")
for q in sys.argv[2:]:
    price, profit, status = price_for(float(q), freight)
    print(f"  quote ${float(q):.2f} → Iraq price {price:,} IQD, profit/order {profit:,.0f} IQD [{status}]")
