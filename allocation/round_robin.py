class RoundRobinAllocator:
    def __init__(self):
        self.name = 'Round Robin'

    def allocate(self, network):
        slices = list(network.slices.values())
        
        # 1. Give each slice its min_bandwidth first (capped at max_bandwidth)
        for s in slices:
            s.allocated_bandwidth = min(s.min_bandwidth, s.max_bandwidth)
            
        remaining = network.total_bandwidth - sum(s.allocated_bandwidth for s in slices)
        if remaining <= 0:
            return
            
        # Distribute remaining equally among slices that need more bandwidth
        max_iterations = 20
        while remaining > 0.01 and max_iterations > 0:
            max_iterations -= 1
            # Needy slices can take more bandwidth without exceeding demand or max_bandwidth
            needy_slices = [
                s for s in slices 
                if s.allocated_bandwidth < min(s.current_demand, s.max_bandwidth)
            ]
            if not needy_slices:
                break
                
            share = remaining / len(needy_slices)
            allocated_this_round = 0.0
            
            for s in needy_slices:
                max_allowed = min(s.current_demand, s.max_bandwidth)
                deficit = max_allowed - s.allocated_bandwidth
                allocation = min(share, deficit)
                
                s.allocated_bandwidth += allocation
                remaining -= allocation
                allocated_this_round += allocation
                
            if allocated_this_round < 0.001:
                break
