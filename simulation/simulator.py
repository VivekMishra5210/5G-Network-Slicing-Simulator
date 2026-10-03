import pandas as pd
from config.config import SLICE_CONFIG, TOTAL_BANDWIDTH, SIM_DURATION
from models.network_model import Network
from models.slice_model import NetworkSlice
from models.user_model import User
from traffic.traffic_generator import TrafficGenerator
from allocation.static_allocator import StaticAllocator
from allocation.round_robin import RoundRobinAllocator
from allocation.qos_allocator import QoSAllocator
from simulation.scenarios import SCENARIOS


class Simulator:
    def __init__(self, total_bandwidth=None, duration=None, seed=42):
        self.total_bandwidth = total_bandwidth or TOTAL_BANDWIDTH
        self.duration = duration or SIM_DURATION
        self.seed = seed

    def _setup_network(self):
        network = Network(total_bandwidth=self.total_bandwidth)
        for slice_type, cfg in SLICE_CONFIG.items():
            s = NetworkSlice(
                name=slice_type,
                slice_type=slice_type,
                priority=cfg['priority'],
                min_bandwidth=cfg['min_bw'],
                max_bandwidth=cfg['max_bw'],
                latency_requirement=cfg['latency_req'],
                packet_loss_requirement=cfg['packet_loss_req']
            )
            # Create users for this slice
            num_users = cfg['base_users']
            for i in range(num_users):
                user = User(
                    user_id=f"{slice_type}_user_{i}",
                    slice_type=slice_type,
                    traffic_demand=cfg['traffic_per_user']
                )
                s.add_user(user)
            network.add_slice(s)
        return network

    def run(self, scenario_name='normal', allocator=None):
        network = self._setup_network()
        traffic_gen = TrafficGenerator(seed=self.seed)
        results = []

        for time_step in range(self.duration):
            # Reset allocations but preserve qos_satisfied from previous step
            # so the QoS allocator can react to violations
            for s in network.slices.values():
                s.allocated_bandwidth = 0
                s.measured_throughput = 0
                s.measured_latency = 0
                s.measured_packet_loss = 0

            # Generate traffic demands
            demands = traffic_gen.generate(time_step, scenario_name, SLICE_CONFIG)

            for slice_type, demand in demands.items():
                if slice_type in network.slices:
                    network.slices[slice_type].current_demand = demand

            # Allocate resources
            if allocator:
                allocator.allocate(network)

            # Calculate metrics
            load_ratio = network.get_load_ratio()

            for slice_type, slice_obj in network.slices.items():
                slice_obj.calculate_metrics(load_ratio)
                slice_obj.check_qos()
                slice_obj.record_step(time_step)

                results.append({
                    'time': time_step,
                    'algorithm': allocator.name if allocator else 'None',
                    'scenario': scenario_name,
                    'slice': slice_type,
                    'demand': round(slice_obj.current_demand, 2),
                    'allocation': round(slice_obj.allocated_bandwidth, 2),
                    'throughput': round(slice_obj.measured_throughput, 2),
                    'latency': round(slice_obj.measured_latency, 2),
                    'packet_loss': round(slice_obj.measured_packet_loss, 2),
                    'utilization': round(
                        (slice_obj.allocated_bandwidth / self.total_bandwidth) * 100, 2
                    ),
                    'qos_satisfied': slice_obj.qos_satisfied
                })

        return pd.DataFrame(results)

    def run_all_algorithms(self, scenario_name='normal'):
        allocators = [StaticAllocator(), RoundRobinAllocator(), QoSAllocator()]
        dfs = []
        for allocator in allocators:
            df = self.run(scenario_name, allocator)
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def run_all_experiments(self):
        dfs = []
        for scenario_name in SCENARIOS.keys():
            df = self.run_all_algorithms(scenario_name)
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
