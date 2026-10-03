TOTAL_BANDWIDTH = 100
SIM_DURATION = 60
TIME_STEP = 1

SLICE_CONFIG = {
    'eMBB': {'priority': 3, 'min_bw': 20, 'max_bw': 60, 'latency_req': 100, 'packet_loss_req': 5.0, 'base_users': 20, 'traffic_per_user': 2.0},
    'URLLC': {'priority': 5, 'min_bw': 10, 'max_bw': 50, 'latency_req': 5, 'packet_loss_req': 1.0, 'base_users': 10, 'traffic_per_user': 1.0},
    'mMTC': {'priority': 2, 'min_bw': 5, 'max_bw': 30, 'latency_req': 200, 'packet_loss_req': 10.0, 'base_users': 200, 'traffic_per_user': 0.05}
}

ALLOCATION_RATIOS = {
    'eMBB': 0.50,
    'URLLC': 0.30,
    'mMTC': 0.20
}

BASE_LATENCY = {
    'eMBB': 10,
    'URLLC': 2,
    'mMTC': 20
}
