import json
import os
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

def generate_comparison_chart(results):
    df = pd.DataFrame(results)

    fig, ax1 = plt.subplots(figsize=(12, 7))

    # Bar chart for RPS
    color_rps = 'tab:green'
    ax1.set_xlabel('Experiment Step')
    ax1.set_ylabel('RPS (Throughput)', color=color_rps)
    bars = ax1.bar(df['name'], df['rps'], color=color_rps, alpha=0.3, label='RPS')
    ax1.tick_params(axis='y', labelcolor=color_rps)

    # Line chart for Latencies
    ax2 = ax1.twinx()
    color_p50 = 'tab:blue'
    color_p95 = 'tab:orange'
    ax2.set_ylabel('Latency (ms)', color='black')
    ax2.plot(df['name'], df['p50'], label='p50 Latency', marker='o', color=color_p50, linewidth=2)
    ax2.plot(df['name'], df['p95'], label='p95 Latency', marker='s', color=color_p95, linewidth=2)
    ax2.tick_params(axis='y', labelcolor='black')

    # Adding values on top of bars
    for bar in bars:
        height = bar.get_height()
        ax1.annotate(f'{height:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')

    plt.title('Database Indexing Experiment Results\nIncremental impact of indexes on /offers endpoint')

    # Combine legends
    lines, labels = ax2.get_legend_handles_labels()
    bars_h, bars_l = ax1.get_legend_handles_labels()
    ax2.legend(bars_h + lines, bars_l + labels, loc='upper left')

    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig('../test results/important/index_experiment_comparison.png')
    print("Comparison chart saved as index_experiment_comparison.png")

def main():
    steps = [
        ("Step 0: Baseline", "step0_baseline"),
        ("Step 1: +Photos Index", "step1_photos_idx"),
        ("Step 2: +Reservations Index", "step2_reservations_idx"),
        ("Step 3: +CreatedAt Index", "step3_createdat_idx")
    ]

    results = []
    for display_name, file_prefix in steps:
        # Find the latest json file for this prefix
        json_files = sorted(Path('../test results/important').glob(f"{file_prefix}_*.json"))
        if not json_files:
            print(f"Warning: No file found for {file_prefix}")
            continue

        with open(json_files[-1], 'r') as f:
            data = json.load(f)
            results.append({
                "name": display_name,
                "rps": data['rps'],
                "p50": data['latency_ms']['p50'],
                "p95": data['latency_ms']['p95']
            })

    if results:
        generate_comparison_chart(results)

if __name__ == "__main__":
    main()
