SCENARIOS = {
    'normal': {
        'description': 'Normal traffic conditions for all slices',
        'traffic_type': 'normal'
    },
    'heavy_embb': {
        'description': 'High demand on eMBB slice (e.g. video streaming event)',
        'traffic_type': 'heavy_embb'
    },
    'urllc_emergency': {
        'description': 'Sudden spike in URLLC traffic',
        'traffic_type': 'urllc_emergency'
    },
    'full_congestion': {
        'description': 'High demand across all network slices causing severe congestion',
        'traffic_type': 'full_congestion'
    },
    'dynamic': {
        'description': 'Time-varying traffic patterns representing changing conditions',
        'traffic_type': 'dynamic'
    }
}
