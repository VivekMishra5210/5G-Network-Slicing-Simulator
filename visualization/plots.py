import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import os

class Visualizer:
    def __init__(self, output_dir='results/graphs'):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        try:
            plt.style.use('seaborn-v0_8-darkgrid')
        except:
            plt.style.use('ggplot')
            
        self.colors = {'eMBB': '#2196F3', 'URLLC': '#F44336', 'mMTC': '#4CAF50'}
        self.qos_latency = {'URLLC': 5, 'eMBB': 100, 'mMTC': 200}
        
    def plot_throughput_over_time(self, df, scenario, algorithm=None, save=True):
        plt.figure(figsize=(10, 6))
        data = df[df['scenario'] == scenario]
        if algorithm:
            data = data[data['algorithm'] == algorithm]
            title_algo = f" - {algorithm}"
        else:
            title_algo = ""
            
        for slice_type in ['eMBB', 'URLLC', 'mMTC']:
            slice_data = data[data['slice'] == slice_type]
            if not slice_data.empty:
                plt.plot(slice_data['time'], slice_data['throughput'], label=slice_type, color=self.colors[slice_type])
                
        plt.title(f'Throughput Over Time - {scenario}{title_algo}')
        plt.xlabel('Time')
        plt.ylabel('Throughput (Mbps)')
        plt.legend()
        plt.tight_layout()
        
        if save:
            filename = f"throughput_{scenario}{'_' + algorithm if algorithm else ''}.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
            
    def plot_latency_over_time(self, df, scenario, algorithm=None, save=True):
        plt.figure(figsize=(10, 6))
        data = df[df['scenario'] == scenario]
        if algorithm:
            data = data[data['algorithm'] == algorithm]
            title_algo = f" - {algorithm}"
        else:
            title_algo = ""
            
        for slice_type in ['eMBB', 'URLLC', 'mMTC']:
            slice_data = data[data['slice'] == slice_type]
            if not slice_data.empty:
                plt.plot(slice_data['time'], slice_data['latency'], label=slice_type, color=self.colors[slice_type])
                plt.axhline(y=self.qos_latency[slice_type], color=self.colors[slice_type], linestyle='--', alpha=0.5, label=f'{slice_type} QoS Target')
                
        plt.title(f'Latency Over Time - {scenario}{title_algo}')
        plt.xlabel('Time')
        plt.ylabel('Latency (ms)')
        plt.legend()
        plt.tight_layout()
        
        if save:
            filename = f"latency_{scenario}{'_' + algorithm if algorithm else ''}.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
            
    def plot_allocation_over_time(self, df, scenario, algorithm=None, save=True):
        plt.figure(figsize=(10, 6))
        data = df[df['scenario'] == scenario]
        if algorithm:
            data = data[data['algorithm'] == algorithm]
            title_algo = f" - {algorithm}"
        else:
            title_algo = ""
            
        time_points = sorted(data['time'].unique())
        
        allocations = {s: [] for s in ['eMBB', 'URLLC', 'mMTC']}
        
        for t in time_points:
            t_data = data[data['time'] == t]
            for s in ['eMBB', 'URLLC', 'mMTC']:
                s_data = t_data[t_data['slice'] == s]
                if not s_data.empty:
                    allocations[s].append(s_data['allocation'].values[0])
                else:
                    allocations[s].append(0)
                    
        plt.stackplot(time_points, allocations['eMBB'], allocations['URLLC'], allocations['mMTC'], 
                      labels=['eMBB', 'URLLC', 'mMTC'], colors=[self.colors['eMBB'], self.colors['URLLC'], self.colors['mMTC']])
        
        plt.title(f'Bandwidth Allocation Over Time - {scenario}{title_algo}')
        plt.xlabel('Time')
        plt.ylabel('Bandwidth Allocation (Mbps)')
        plt.legend(loc='upper left')
        plt.tight_layout()
        
        if save:
            filename = f"allocation_{scenario}{'_' + algorithm if algorithm else ''}.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
            
    def plot_packet_loss(self, df, scenario, save=True):
        plt.figure(figsize=(10, 6))
        data = df[df['scenario'] == scenario]
        
        if not data.empty:
            summary = data.groupby(['algorithm', 'slice'])['packet_loss'].mean().unstack()
            if not summary.empty:
                summary.plot(kind='bar', color=[self.colors.get(x, '#333') for x in summary.columns], ax=plt.gca())
            
        plt.title(f'Average Packet Loss Comparison - {scenario}')
        plt.xlabel('Algorithm')
        plt.ylabel('Packet Loss (%)')
        plt.legend(title='Slice Type')
        plt.tight_layout()
        
        if save:
            filename = f"packet_loss_{scenario}.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
            
    def plot_qos_satisfaction(self, df, save=True):
        plt.figure(figsize=(10, 6))
        
        if not df.empty:
            summary = df.groupby(['algorithm', 'slice'])['qos_satisfied'].mean() * 100
            summary = summary.unstack()
            if not summary.empty:
                summary.plot(kind='bar', color=[self.colors.get(x, '#333') for x in summary.columns], ax=plt.gca())
            
        plt.title('QoS Satisfaction Percentage by Algorithm and Slice (All Scenarios)')
        plt.xlabel('Algorithm')
        plt.ylabel('QoS Satisfaction (%)')
        plt.legend(title='Slice Type')
        plt.ylim(0, 105)
        plt.tight_layout()
        
        if save:
            filename = "qos_satisfaction_summary.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
            
    def plot_resource_utilization(self, df, scenario, save=True):
        plt.figure(figsize=(10, 6))
        data = df[df['scenario'] == scenario]
        
        algorithms = data['algorithm'].unique()
        for algo in algorithms:
            algo_data = data[data['algorithm'] == algo]
            utilization = algo_data.groupby('time')['utilization'].mean() * 100
            plt.plot(utilization.index, utilization.values, label=algo)
            
        plt.title(f'Resource Utilization Over Time - {scenario}')
        plt.xlabel('Time')
        plt.ylabel('Utilization (%)')
        plt.legend()
        plt.tight_layout()
        
        if save:
            filename = f"utilization_{scenario}.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
            
    def plot_algorithm_comparison(self, df, save=True):
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        if not df.empty:
            # Avg Throughput
            throughput = df.groupby('algorithm')['throughput'].mean()
            throughput.plot(kind='bar', ax=axes[0,0], color='skyblue')
            axes[0,0].set_title('Average Throughput')
            axes[0,0].set_ylabel('Mbps')
            
            # Avg Latency
            latency = df.groupby('algorithm')['latency'].mean()
            latency.plot(kind='bar', ax=axes[0,1], color='salmon')
            axes[0,1].set_title('Average Latency')
            axes[0,1].set_ylabel('ms')
            
            # Avg Packet Loss
            loss = df.groupby('algorithm')['packet_loss'].mean()
            loss.plot(kind='bar', ax=axes[1,0], color='lightgreen')
            axes[1,0].set_title('Average Packet Loss')
            axes[1,0].set_ylabel('%')
            
            # QoS Satisfaction
            qos = df.groupby('algorithm')['qos_satisfied'].mean() * 100
            qos.plot(kind='bar', ax=axes[1,1], color='gold')
            axes[1,1].set_title('QoS Satisfaction')
            axes[1,1].set_ylabel('%')
        
        plt.suptitle('Overall Algorithm Comparison', fontsize=16)
        plt.tight_layout()
        
        if save:
            filename = "algorithm_comparison_summary.png"
            plt.savefig(os.path.join(self.output_dir, filename))
            plt.close()
            
    def generate_all_plots(self, df):
        saved_files = []
        if df.empty:
            return saved_files
            
        scenarios = df['scenario'].unique()
        algorithms = df['algorithm'].unique()
        
        self.plot_qos_satisfaction(df)
        self.plot_algorithm_comparison(df)
        
        for scenario in scenarios:
            self.plot_packet_loss(df, scenario)
            self.plot_resource_utilization(df, scenario)
            
            for algo in algorithms:
                self.plot_throughput_over_time(df, scenario, algo)
                self.plot_latency_over_time(df, scenario, algo)
                self.plot_allocation_over_time(df, scenario, algo)
                
        return saved_files
