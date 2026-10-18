import os
import sys
import pandas as pd
from flask import Flask, request, jsonify, render_template

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulation.simulator import Simulator
from allocation.static_allocator import StaticAllocator
from allocation.round_robin import RoundRobinAllocator
from allocation.qos_allocator import QoSAllocator
from config.config import TOTAL_BANDWIDTH, SIM_DURATION, SLICE_CONFIG

# MCRA Imports
from mcra.simulation import MCRASimulator
from mcra.models import TopologyMode

app = Flask(__name__)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/mcra/simulate', methods=['POST'])
def mcra_simulate():
    """
    Dedicated endpoint for the research-grounded MCRA packet-flow simulation mode.
    """
    data = request.json or {}

    try:
        # Validate and parse parameters
        raw_topo = data.get('topology_mode', 'parallel_hybrid').lower()
        if raw_topo in ['edge_only', 'edge']:
            topo_mode = TopologyMode.EDGE_ONLY
        elif raw_topo in ['cloud_only', 'cloud']:
            topo_mode = TopologyMode.CLOUD_ONLY
        else:
            topo_mode = TopologyMode.PARALLEL_HYBRID

        scenario = str(data.get('scenario', 'normal_mix')).lower().replace(' ', '_')
        duration_ms = float(data.get('duration_ms', 1000.0))
        if duration_ms <= 0 or duration_ms > 30000:
            return jsonify({'error': 'duration_ms must be between 1 and 30000 ms'}), 400

        seed = int(data.get('seed', 42))
        cost_base = float(data.get('cost_base', 2.0))
        if cost_base <= 1.0:
            return jsonify({'error': 'cost_base delta must be strictly greater than 1.0'}), 400

        access_link_capacity_mbps = float(data.get('access_link_capacity_mbps', 100.0))
        backhaul_capacity_mbps = float(data.get('backhaul_capacity_mbps', 50.0))
        edge_compute_capacity = float(data.get('edge_compute_capacity', 30.0))
        cloud_compute_capacity = float(data.get('cloud_compute_capacity', 150.0))

        if any(c <= 0 for c in [access_link_capacity_mbps, backhaul_capacity_mbps, edge_compute_capacity, cloud_compute_capacity]):
            return jsonify({'error': 'All link and compute capacities must be strictly positive'}), 400

        comm_increment = float(data.get('comm_increment_mbps', 1.0))
        compute_increment = float(data.get('compute_increment_units', 0.5))
        num_tenants = int(data.get('num_tenants', 2))
        arrival_rate_scale = float(data.get('arrival_rate_scale', 1.0))

        simulator = MCRASimulator(
            topology_mode=topo_mode,
            seed=seed,
            cost_base=cost_base,
            comm_increment_mbps=comm_increment,
            compute_increment_units=compute_increment,
            access_link_capacity_mbps=access_link_capacity_mbps,
            backhaul_capacity_mbps=backhaul_capacity_mbps,
            edge_compute_capacity=edge_compute_capacity,
            cloud_compute_capacity=cloud_compute_capacity,
        )

        results = simulator.run(
            scenario=scenario,
            duration_ms=duration_ms,
            num_tenants=num_tenants,
            arrival_rate_scale=arrival_rate_scale,
        )

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'MCRA simulation error: {str(e)}'}), 500


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """
    Main simulation endpoint supporting legacy algorithms (Static, Round Robin, QoS Adaptive)
    and additive routing to MCRA when requested.
    """
    data = request.json or {}

    algorithm = data.get('algorithm', 'all').strip()

    # Route MCRA requests to the dedicated MCRA engine
    if algorithm.lower() == 'mcra':
        return mcra_simulate()

    bandwidth = float(data.get('bandwidth', TOTAL_BANDWIDTH))
    duration = int(data.get('duration', SIM_DURATION))
    scenario = data.get('scenario', 'normal')
    seed = int(data.get('seed', 42))

    sim = Simulator(total_bandwidth=bandwidth, duration=duration, seed=seed)

    if algorithm.lower() == 'all':
        df = sim.run_all_algorithms(scenario)
    else:
        allocator = None
        if algorithm.lower() == 'static':
            allocator = StaticAllocator()
        elif algorithm.lower() == 'round robin':
            allocator = RoundRobinAllocator()
        elif algorithm.lower() == 'qos adaptive':
            allocator = QoSAllocator()

        if allocator:
            df = sim.run(scenario, allocator)
        else:
            return jsonify({'error': 'Invalid algorithm'}), 400

    # Build per-slice summary
    summary = {}
    comparison = {}

    for slice_name in df['slice'].unique():
        slice_df = df[df['slice'] == slice_name]
        summary[slice_name] = {
            'avg_throughput': round(float(slice_df['throughput'].mean()), 2),
            'avg_latency': round(float(slice_df['latency'].mean()), 2),
            'avg_packet_loss': round(float(slice_df['packet_loss'].mean()), 2),
            'qos_satisfaction': round(float(slice_df['qos_satisfied'].mean() * 100), 2)
        }

    # Build per-algorithm comparison if running all
    if algorithm.lower() == 'all':
        for algo in df['algorithm'].unique():
            algo_df = df[df['algorithm'] == algo]
            algo_summary = {}
            for slice_name in algo_df['slice'].unique():
                slice_df = algo_df[algo_df['slice'] == slice_name]
                algo_summary[slice_name] = {
                    'avg_throughput': round(float(slice_df['throughput'].mean()), 2),
                    'avg_latency': round(float(slice_df['latency'].mean()), 2),
                    'avg_packet_loss': round(float(slice_df['packet_loss'].mean()), 2),
                    'qos_satisfaction': round(float(slice_df['qos_satisfied'].mean() * 100), 2)
                }
            comparison[algo] = algo_summary

    return jsonify({
        'results': df.fillna(0).to_dict(orient='records'),
        'summary': summary,
        'comparison': comparison
    })


if __name__ == '__main__':
    app.run(port=5000, debug=True)
