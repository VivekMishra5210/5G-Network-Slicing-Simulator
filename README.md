# 5G Network Slicing Simulator

A Python-based simulator for exploring resource allocation in 5G network slices. Evaluate algorithms across eMBB, URLLC, and mMTC slices.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Project Structure
```
.
├── config/
├── simulation/
├── allocation/
├── metrics/
├── visualization/
├── experiments/
├── dashboard/
├── results/
├── main.py
└── requirements.txt
```

## Features
- Simulated scenarios for various network demands.
- Multiple allocation algorithms (Static, Dynamic).
- Detailed visualization of throughput, latency, and packet loss.
- Flask dashboard for interactive data visualization.

## How to use the dashboard
Run the dashboard with:
```bash
python main.py --dashboard
```
Then navigate to `http://localhost:5000` in your browser.

## How to run experiments
Execute the experiment runner to test all scenarios and algorithms:
```bash
python -m experiments.run_experiments
```

## Tech Stack
- Python 3
- Pandas, NumPy
- Matplotlib
- Flask

## Screenshots
*(Add screenshots of plots and dashboard here)*
