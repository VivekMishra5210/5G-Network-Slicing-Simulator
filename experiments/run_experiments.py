import os
from simulation.simulator import Simulator
from visualization.plots import Visualizer
from metrics.metrics import generate_summary

def main():
    print("Running experiments...")
    
    sim = Simulator()
    df = sim.run_all_experiments()
    
    csv_dir = 'results/csv'
    if not os.path.exists(csv_dir):
        os.makedirs(csv_dir)
    df.to_csv(os.path.join(csv_dir, 'all_results.csv'), index=False)
    
    print("Generating plots...")
    viz = Visualizer()
    viz.generate_all_plots(df)
    
    print("Summary:")
    summary = generate_summary(df)
    for k, v in summary.items():
        print(f"{k}: {v}")
        
    print("Experiments completed.")

if __name__ == '__main__':
    main()
