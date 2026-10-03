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


@app.route('/api/simulate', methods=['POST'])
def simulate():
    data = request.json

    bandwidth = float(data.get('bandwidth', TOTAL_BANDWIDTH))
    duration = int(data.get('duration', SIM_DURATION))
    scenario = data.get('scenario', 'normal')
    algorithm = data.get('algorithm', 'all')
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
