import json
import os
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

def plot_benchmark_results(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    steps = data.get('steps', [])
    if not steps:
        print(f"    No steps found in {json_path}")
        return

    df = pd.DataFrame(steps)
    
    # Filter out steps with null latencies (failures)
    df_ok = df.dropna(subset=['p50_ms', 'p95_ms'])
    
    if df_ok.empty:
        print(f"    No valid performance data in {json_path}")
        return

    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Plot Latencies
    color_p50 = 'tab:blue'
    color_p95 = 'tab:orange'
    color_p99 = 'tab:red'
    
    ax1.set_xlabel('Concurrency')
    ax1.set_ylabel('Latency (ms)', color='black')
    ax1.plot(df_ok['concurrency'], df_ok['p50_ms'], label='p50', marker='o', color=color_p50)
    ax1.plot(df_ok['concurrency'], df_ok['p95_ms'], label='p95', marker='s', color=color_p95)
    ax1.plot(df_ok['concurrency'], df_ok['p99_ms'], label='p99', marker='^', color=color_p99)
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.legend(loc='upper left')
    ax1.grid(True, linestyle='--', alpha=0.7)

    # Plot RPS on secondary axis
    ax2 = ax1.twinx()
    color_rps = 'tab:green'
    ax2.set_ylabel('RPS (Requests per second)', color=color_rps)
    ax2.plot(df_ok['concurrency'], df_ok['rps'], label='RPS', marker='x', color=color_rps, linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color_rps)
    ax2.legend(loc='upper right')

    title = f"Benchmark: {data.get('path')} ({data.get('method')})\nFile: {os.path.basename(json_path)}"
    plt.title(title)
    
    output_path = json_path.replace('.json', '.png')
    plt.savefig(output_path)
    print(f"    Chart saved to: {output_path}")
    plt.close()

def main():
    results_dir = Path('../test results/important')
    for json_file in results_dir.glob('*.json'):
        print(f"Processing {json_file}...")
        try:
            plot_benchmark_results(str(json_file))
        except Exception as e:
            print(f"    Error processing {json_file}: {e}")

if __name__ == "__main__":
    main()
