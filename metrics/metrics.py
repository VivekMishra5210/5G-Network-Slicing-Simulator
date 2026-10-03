import pandas as pd

def calculate_qos_satisfaction(history_list):
    if not history_list:
        return 0.0
    satisfied = sum(1 for step in history_list if step.get('qos_satisfied', False))
    return (satisfied / len(history_list)) * 100

def calculate_avg_throughput(history_list):
    if not history_list:
        return 0.0
    return sum(step.get('measured_throughput', 0) for step in history_list) / len(history_list)

def calculate_avg_latency(history_list):
    if not history_list:
        return 0.0
    return sum(step.get('measured_latency', 0) for step in history_list) / len(history_list)

def calculate_avg_packet_loss(history_list):
    if not history_list:
        return 0.0
    return sum(step.get('measured_packet_loss', 0) for step in history_list) / len(history_list)

def generate_summary(data_source, algorithm_name=None, scenario_name=None):
    """
    Accepts either:
    1. A pandas DataFrame containing simulation results
    2. A Network object, algorithm_name, scenario_name
    """
    if isinstance(data_source, pd.DataFrame):
        df = data_source
        summary = {}
        for algo in df['algorithm'].unique():
            algo_df = df[df['algorithm'] == algo]
            summary[algo] = {}
            for s in algo_df['slice'].unique():
                s_df = algo_df[algo_df['slice'] == s]
                summary[algo][s] = {
                    'avg_throughput': round(float(s_df['throughput'].mean()), 2),
                    'avg_latency': round(float(s_df['latency'].mean()), 2),
                    'avg_packet_loss': round(float(s_df['packet_loss'].mean()), 2),
                    'qos_satisfaction': round(float(s_df['qos_satisfied'].mean() * 100), 2)
                }
        return summary

    # Network object case
    network = data_source
    summary = {
        'algorithm': algorithm_name or 'Unknown',
        'scenario': scenario_name or 'Unknown',
        'slices': {}
    }
    
    for name, slice_obj in network.slices.items():
        summary['slices'][name] = {
            'avg_throughput': calculate_avg_throughput(slice_obj.history),
            'avg_latency': calculate_avg_latency(slice_obj.history),
            'avg_packet_loss': calculate_avg_packet_loss(slice_obj.history),
            'qos_satisfaction': calculate_qos_satisfaction(slice_obj.history)
        }
        
    return summary
