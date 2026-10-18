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
    parser = argparse.ArgumentParser(description="5G Network Slicing Simulator (with MCRA)")
    parser.add_argument('--scenario', type=str, default='dynamic',
                        help="Traffic scenario to simulate (e.g. normal, dynamic, normal_mix, embb_surge)")
    parser.add_argument('--algorithm', type=str, default='all',
                        choices=['all', 'static', 'round_robin', 'qos_adaptive', 'mcra'],
                        help="Allocation algorithm")
    parser.add_argument('--topology_mode', type=str, default='parallel_hybrid',
                        choices=['parallel_hybrid', 'edge_only', 'cloud_only'],
                        help="MCRA topology mode")
    parser.add_argument('--bandwidth', type=float, default=100, help="Total bandwidth in Mbps")
    parser.add_argument('--duration', type=int, default=60, help="Simulation duration in seconds (or ms for MCRA)")
    parser.add_argument('--seed', type=int, default=42, help="Random seed")
    parser.add_argument('--cost_base', type=float, default=2.0, help="MCRA cost base delta")
    parser.add_argument('--dashboard', action='store_true', help="Launch the Flask dashboard")

    args = parser.parse_args()

    if args.dashboard:
        from dashboard.app import app
        print("Starting 5G Network Slicing Dashboard on http://localhost:5000")
        app.run(debug=True, port=5000)
    elif args.algorithm == 'mcra':
        from mcra.simulation import MCRASimulator
        from mcra.models import TopologyMode
        import pandas as pd

        topo_mode = {
            'edge_only': TopologyMode.EDGE_ONLY,
            'cloud_only': TopologyMode.CLOUD_ONLY,
            'parallel_hybrid': TopologyMode.PARALLEL_HYBRID,
        }.get(args.topology_mode, TopologyMode.PARALLEL_HYBRID)

        scenario_name = args.scenario if args.scenario in [
            'normal_mix', 'embb_surge', 'urllc_emergency', 'mmtc_surge', 'edge_overload',
            'backhaul_congestion', 'mixed_peak', 'dynamic_day', 'trace_playback', '5g_nr_trace_playback', 'ns3_trace'
        ] else 'normal_mix'

        duration_ms = 1000.0 if args.duration == 60 else float(args.duration if args.duration >= 100 else args.duration * 1000)

        print(f"\n[MCRA] Running Research-Grounded MCRA Simulation (Topology: {topo_mode.value}, Scenario: {scenario_name}, Seed: {args.seed})")
        sim = MCRASimulator(topology_mode=topo_mode, seed=args.seed, cost_base=args.cost_base)
        res = sim.run(scenario=scenario_name, duration_ms=duration_ms)

        # Save results to CSV
        os.makedirs('results/mcra', exist_ok=True)
        csv_path = f"results/mcra/mcra_{scenario_name}_{topo_mode.value}.csv"
        df = pd.DataFrame(res['requests'])
        df.to_csv(csv_path, index=False)
        print(f"[MCRA] Detailed request logs saved to {csv_path}")

        # Print Summary
        summary = res['summary']
        print("\n" + "=" * 70)
        print("MCRA TWO-TIER SIMULATION RESULTS SUMMARY")
        print("=" * 70)
        print(f"Total Offered Requests   : {summary['total_offered_requests']}")
        print(f"Total Admitted Requests  : {summary['total_admitted_requests']}")
        print(f"Total Completed Requests : {summary['total_completed_requests']}")
        print(f"Total Blocked Requests   : {summary['total_blocked_requests']}")
        print(f"Blocking Probability     : {summary['blocking_probability'] * 100:.2f}%")
        print(f"Delivered Throughput     : {summary['delivered_throughput_mbps']:.3f} Mbps")
        print(f"Mean E2E Delay           : {summary['mean_e2e_delay_ms']:.2f} ms")
        print(f"P95 E2E Delay            : {summary['p95_delay_ms']:.2f} ms")
        print(f"Avg MCRA Iterations      : {summary['avg_mcra_iterations']:.2f}")

        print("\n--- Per-Slice Performance ---")
        print(f"{'Slice':<10} {'Offered':>8} {'Completed':>10} {'Blocked':>8} {'Mean Delay':>12} {'QoS %':>8}")
        print("-" * 62)
        for s_name, s_data in res['per_slice'].items():
            print(f"{s_name:<10} {s_data['offered_requests']:>8} {s_data['completed_requests']:>10} "
                  f"{s_data['blocked_requests']:>8} {s_data['mean_e2e_delay_ms']:>10.2f} ms "
                  f"{s_data['qos_satisfaction_pct']:>7.1f}%")

        print("\n--- Time-Weighted Resource Utilization ---")
        for r_id, u_val in res['resource_utilization'].items():
            print(f"  {r_id:<20}: {u_val:>6.2f}%")
        print("=" * 70)

    else:
        # Legacy Simulation Pipeline (Static, Round Robin, QoS Adaptive, All)
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
