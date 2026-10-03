from config.config import BASE_LATENCY

class NetworkSlice:
    def __init__(self, name, slice_type, priority, min_bandwidth, max_bandwidth, latency_requirement, packet_loss_requirement):
        self.name = name
        self.slice_type = slice_type
        self.priority = priority
        self.min_bandwidth = min_bandwidth
        self.max_bandwidth = max_bandwidth
        self.latency_requirement = latency_requirement
        self.packet_loss_requirement = packet_loss_requirement
        
        self.users = []
        self.current_demand = 0
        self.allocated_bandwidth = 0
        self.measured_throughput = 0
        self.measured_latency = 0
        self.measured_packet_loss = 0
        self.qos_satisfied = True
        self.history = []

    def add_user(self, user):
        self.users.append(user)

    def update_demand(self, total_demand):
        self.current_demand = total_demand

    def calculate_metrics(self, network_load_ratio):
        self.measured_throughput = min(self.current_demand, self.allocated_bandwidth)
        
        if self.current_demand > self.allocated_bandwidth and self.current_demand > 0:
            self.measured_packet_loss = ((self.current_demand - self.allocated_bandwidth) / self.current_demand) * 100
        else:
            self.measured_packet_loss = 0
            
        base_latency = BASE_LATENCY.get(self.slice_type, 10)
        self.measured_latency = base_latency * (1 + 2.0 * network_load_ratio)
        
        if self.allocated_bandwidth > 0:
            self.measured_latency += max(0, (self.current_demand - self.allocated_bandwidth) / self.allocated_bandwidth) * 5
            
    def check_qos(self):
        self.qos_satisfied = (self.measured_latency <= self.latency_requirement) and (self.measured_packet_loss <= self.packet_loss_requirement)
        return self.qos_satisfied

    def record_step(self, time):
        self.history.append({
            'time': time,
            'demand': self.current_demand,
            'allocated': self.allocated_bandwidth,
            'throughput': self.measured_throughput,
            'latency': self.measured_latency,
            'packet_loss': self.measured_packet_loss,
            'qos_satisfied': self.qos_satisfied
        })

    def reset(self):
        self.current_demand = 0
        self.allocated_bandwidth = 0
        self.measured_throughput = 0
        self.measured_latency = 0
        self.measured_packet_loss = 0
        self.qos_satisfied = True

    def __repr__(self):
        return f"NetworkSlice(name={self.name}, type={self.slice_type}, demand={self.current_demand}, allocated={self.allocated_bandwidth})"
