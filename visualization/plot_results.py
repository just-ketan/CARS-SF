import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv(
    "results/allocation_results.csv"
)

contexts = df["context"].unique()

for context in contexts:

    subset = df[
        df["context"] == context
    ]

    services = subset["service"]

    demand = subset["demand"]

    allocation = subset["allocation"]

    plt.figure(figsize=(8, 5))

    x = range(len(services))

    plt.bar(
        [i - 0.2 for i in x],
        demand,
        width=0.4,
        label="Demand"
    )

    plt.bar(
        [i + 0.2 for i in x],
        allocation,
        width=0.4,
        label="Allocation"
    )

    plt.xticks(x, services)

    plt.ylabel("Bandwidth (Mbps)")

    plt.title(
        f"{context.upper()} Context"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        f"results/{context}_allocation.png"
    )

    plt.close()

print(
    "Plots generated successfully."
)
