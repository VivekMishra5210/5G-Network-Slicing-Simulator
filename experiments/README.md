# Module Documentation: `experiments/` & Execution Entry Points

## 1. Overview
This module contains the automated benchmarking scripts, batch experimental execution pipelines, and command-line entry points.

---

## 2. File Deep-Dive

### 2.1. `experiments/run_experiments.py` — Batch Experiment Pipeline

#### Purpose
Executes a full matrix of experimental benchmarks across all scenarios and algorithms without user intervention.

#### Execution Pipeline
```python
def main():
    sim = Simulator()
    df = sim.run_all_experiments()
    df.to_csv('results/csv/all_results.csv', index=False)
    
    viz = Visualizer()
    viz.generate_all_plots(df)
    
    summary = generate_summary(df)
    for algo, stats in summary.items():
        print(f"{algo}: {stats}")
```
*   **Total Combinations Tested:** 5 Scenarios $\times$ 3 Algorithms = **15 full 60-second simulations** (900 data points per slice, 2,700 data rows total).
*   **Artifacts Generated:**
    *   `results/csv/all_results.csv`: Master data export.
    *   `results/graphs/*.png`: 30+ publication-ready performance plots.

#### How to Run:
```bash
python -m experiments.run_experiments
```

---

### 2.2. `main.py` — Unified CLI & Server Entry Point

#### Purpose
The primary command-line interface for the entire project. Supports both quick headless simulation runs and launching the web server.

#### Supported CLI Arguments
*   `--scenario`: Traffic scenario to execute (`'normal'`, `'heavy_embb'`, `'urllc_emergency'`, `'full_congestion'`, or `'dynamic'`, default: `'dynamic'`).
*   `--algorithm`: Allocator to evaluate (`'all'`, `'static'`, `'round_robin'`, or `'qos_adaptive'`, default: `'all'`).
*   `--bandwidth`: Total available bandwidth in Mbps (default: `100`).
*   `--duration`: Duration in seconds (default: `60`).
*   `--seed`: Pseudo-random seed for traffic generation (default: `42`).
*   `--dashboard`: Boolean flag to launch the Flask interactive web dashboard.

#### CLI Command Examples

##### 1. Run Dynamic Scenario (Comparing all 3 algorithms):
```bash
python main.py --scenario dynamic
```
*Outputs an ASCII formatted summary table in the terminal and saves plots to `results/graphs/`.*

##### 2. Run Heavy eMBB Congestion under QoS Adaptive allocator only:
```bash
python main.py --scenario heavy_embb --algorithm qos_adaptive
```

##### 3. Launch the Interactive Web Dashboard:
```bash
python main.py --dashboard
```
*Spawns the local web server on [http://localhost:5000](http://localhost:5000).*

---

## 3. Terminal Output Demonstration

When executing `python main.py --scenario dynamic`, the script outputs:

```text
Running all algorithms on scenario: dynamic
Results saved to results/csv/dynamic_all.csv
Plots saved to results/graphs/

======================================================================
SIMULATION RESULTS SUMMARY
======================================================================

--- Static ---
Slice        Throughput      Latency     Pkt Loss      QoS %
----------------------------------------------------------
eMBB            42.67       27.20       12.90      66.7%
URLLC           15.78        5.99        7.86      50.0%
mMTC            10.39       52.26        0.00     100.0%

--- Round Robin ---
Slice        Throughput      Latency     Pkt Loss      QoS %
----------------------------------------------------------
eMBB            46.01       26.75        8.81      66.7%
URLLC           18.93        5.37        2.28      50.0%
mMTC            10.39       52.26        0.00     100.0%

--- QoS Adaptive ---
Slice        Throughput      Latency     Pkt Loss      QoS %
----------------------------------------------------------
eMBB            46.01       26.75        8.81      66.7%
URLLC           19.11        5.35        1.98      50.0%
mMTC            10.21       52.39        1.71      95.0%
======================================================================
```

---

## 4. Viva / Defense Preparation Questions
1. **Q:** *Why is a unified CLI entry point important in a research simulator?*
   * **A:** It decouples experimental automation from code modification. Different network scenarios, seeds, and algorithms can be systematically executed and scripted into automated test harnesses.
2. **Q:** *Where are the CSV exports stored and how can they be used?*
   * **A:** All results are written to `results/csv/`. They contain raw per-second telemetry that can be independently imported into external data analysis suites like R, Jupyter Notebooks, or MATLAB.
