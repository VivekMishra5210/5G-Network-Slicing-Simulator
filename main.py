import argparse
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation.simulator import Simulator
from allocation.static_allocator import StaticAllocator
from allocation.round_robin import RoundRobinAllocator
from allocation.qos_allocator import QoSAllocator
from visualization.plots import Visualizer


def main():
    parser = argparse.ArgumentParser(description="5G Network Slicing Simulator")
    parser.add_argument('--scenario', type=str, default='dynamic',
                        choices=['normal', 'heavy_embb', 'urllc_emergency', 'full_congestion', 'dynamic'],
                        help="Traffic scenario to simulate")
    parser.add_argument('--algorithm', type=str, default='all',
                        choices=['all', 'static', 'round_robin', 'qos_adaptive'],
                        help="Allocation algorithm")
    parser.add_argument('--bandwidth', type=float, default=100, help="Total bandwidth in Mbps")
    parser.add_argument('--duration', type=int, default=60, help="Simulation duration in seconds")
    parser.add_argument('--seed', type=int, default=42, help="Random seed")
    parser.add_argument('--dashboard', action='store_true', help="Launch the Flask dashboard")

    args = parser.parse_args()

    if args.dashboard:
        from dashboard.app import app
        print("Starting 5G Network Slicing Dashboard on http://localhost:5000")
        app.run(debug=True, port=5000)
    else:
        sim = Simulator(total_bandwidth=args.bandwidth, duration=args.duration, seed=args.seed)

        if args.algorithm == 'all':
            print(f"Running all algorithms on scenario: {args.scenario}")
            df = sim.run_all_algorithms(args.scenario)
        else:
            allocators = {
                'static': StaticAllocator(),
                'round_robin': RoundRobinAllocator(),
                'qos_adaptive': QoSAllocator()
            }
            allocator = allocators[args.algorithm]
            print(f"Running {allocator.name} on scenario: {args.scenario}")
            df = sim.run(args.scenario, allocator)

        # Save results
        os.makedirs('results/csv', exist_ok=True)
        csv_path = f"results/csv/{args.scenario}_{args.algorithm}.csv"
        df.to_csv(csv_path, index=False)
        print(f"Results saved to {csv_path}")

        # Generate plots
        viz = Visualizer()
        viz.generate_all_plots(df)
        print("Plots saved to results/graphs/")

        # Print summary table
        print("\n" + "=" * 70)
        print("SIMULATION RESULTS SUMMARY")
        print("=" * 70)
        for algo in df['algorithm'].unique():
            algo_df = df[df['algorithm'] == algo]
            print(f"\n--- {algo} ---")
            print(f"{'Slice':<10} {'Throughput':>12} {'Latency':>12} {'Pkt Loss':>12} {'QoS %':>10}")
            print("-" * 58)
            for s in ['eMBB', 'URLLC', 'mMTC']:
                s_df = algo_df[algo_df['slice'] == s]
                if not s_df.empty:
                    print(f"{s:<10} {s_df['throughput'].mean():>10.2f}  {s_df['latency'].mean():>10.2f}  "
                          f"{s_df['packet_loss'].mean():>10.2f}  {s_df['qos_satisfied'].mean() * 100:>8.1f}%")
        print("=" * 70)


if __name__ == '__main__':
    main()
