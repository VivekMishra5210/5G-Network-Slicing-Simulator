from config.config import ALLOCATION_RATIOS

class StaticAllocator:
    def __init__(self):
        self.name = 'Static'

    def allocate(self, network):
        for slice_obj in network.slices.values():
            ratio = ALLOCATION_RATIOS.get(slice_obj.slice_type, 0)
            slice_obj.allocated_bandwidth = network.total_bandwidth * ratio
