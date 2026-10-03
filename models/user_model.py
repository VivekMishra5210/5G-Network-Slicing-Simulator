class User:
    def __init__(self, user_id, slice_type, traffic_demand, packet_size=1500, active=True):
        self.user_id = user_id
        self.slice_type = slice_type
        self.traffic_demand = traffic_demand
        self.packet_size = packet_size
        self.active = active

    def __repr__(self):
        return f"User(id={self.user_id}, slice={self.slice_type}, demand={self.traffic_demand})"
