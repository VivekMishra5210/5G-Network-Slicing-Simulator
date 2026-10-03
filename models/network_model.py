class Network:
    def __init__(self, total_bandwidth):
        self.total_bandwidth = total_bandwidth
        self.slices = {}

    def add_slice(self, network_slice):
        self.slices[network_slice.name] = network_slice

    def get_total_demand(self):
        return sum(s.current_demand for s in self.slices.values())

    def get_utilization(self):
        total_allocated = sum(s.allocated_bandwidth for s in self.slices.values())
        return (total_allocated / self.total_bandwidth) * 100 if self.total_bandwidth > 0 else 0

    def get_load_ratio(self):
        ratio = self.get_total_demand() / self.total_bandwidth if self.total_bandwidth > 0 else 0
        return min(ratio, 1.0)

    def reset_allocations(self):
        for s in self.slices.values():
            s.reset()

    def __repr__(self):
        return f"Network(bandwidth={self.total_bandwidth}, slices={list(self.slices.keys())})"
