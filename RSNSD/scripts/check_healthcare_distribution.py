from collections import Counter

import pandas as pd

df = pd.read_csv(
    "RSNSD/dataset/processed/healthcare_school.csv"
)

counts = Counter(df["application_id"])

print()

print("=" * 60)
print("Healthcare Application Distribution")
print("=" * 60)

total = len(df)

for app, count in counts.items():

    pct = count * 100 / total

    print(f"{app:<35} {count:>5} ({pct:5.2f}%)")

print("=" * 60)