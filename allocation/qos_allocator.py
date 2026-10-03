class QoSAllocator:
    def __init__(self):
        self.name = 'QoS Adaptive'

    def allocate(self, network):
        slices = list(network.slices.values())
        
        # 1. Give each slice its min_bandwidth first (capped at max_bandwidth)
        for s in slices:
            s.allocated_bandwidth = min(s.min_bandwidth, s.max_bandwidth)
            
        remaining = network.total_bandwidth - sum(s.allocated_bandwidth for s in slices)
        if remaining <= 0:
            return
            
        # 2. Calculate priority scores
        scores = {}
        for s in slices:
            base_priority = s.priority
            demand_factor = min(5.0, ((s.current_demand - s.min_bandwidth) / s.min_bandwidth) * 2.0) if s.current_demand > s.min_bandwidth else 0.0
            qos_violation_factor = 5.0 if not s.qos_satisfied else 0.0
            scores[s.slice_type] = max(1.0, base_priority + demand_factor + qos_violation_factor)
            
        max_iterations = 20
        while remaining > 0.01 and max_iterations > 0:
            max_iterations -= 1
            # Only consider slices that have unmet demand AND room below max_bandwidth
            needy_slices = [
                s for s in slices 
                if s.allocated_bandwidth < min(s.current_demand, s.max_bandwidth)
            ]
            if not needy_slices:
                break
                
            total_weight = sum(scores[s.slice_type] * max(1.0, s.current_demand) for s in needy_slices)
            if total_weight <= 0:
                break
                
            allocated_this_round = 0.0
            for s in needy_slices:
                weight = scores[s.slice_type] * max(1.0, s.current_demand)
                share = remaining * (weight / total_weight)
                
                max_allowed = min(s.current_demand, s.max_bandwidth)
                deficit = max_allowed - s.allocated_bandwidth
                allocation = min(share, deficit)
                
                s.allocated_bandwidth += allocation
                remaining -= allocation
                allocated_this_round += allocation
                
            if allocated_this_round < 0.001:
                break
