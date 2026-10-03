import numpy as np

class TrafficGenerator:
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)

    def generate(self, time_step, scenario_name, slices_config):
        demands = {}
        
        current_scenario = scenario_name
        if scenario_name == 'dynamic':
            if 0 <= time_step <= 19:
                current_scenario = 'normal'
            elif 20 <= time_step <= 39:
                current_scenario = 'heavy_embb'
            elif 40 <= time_step <= 49:
                current_scenario = 'urllc_emergency'
            else:
                current_scenario = 'normal'
                
        if current_scenario == 'normal':
            demands['eMBB'] = self.rng.uniform(35, 45)
            demands['URLLC'] = self.rng.uniform(10, 15)
            demands['mMTC'] = self.rng.uniform(8, 12)
        elif current_scenario == 'heavy_embb':
            demands['eMBB'] = self.rng.uniform(70, 95)
            demands['URLLC'] = self.rng.uniform(10, 15)
            demands['mMTC'] = self.rng.uniform(8, 12)
        elif current_scenario == 'urllc_emergency':
            demands['eMBB'] = self.rng.uniform(35, 45)
            demands['URLLC'] = self.rng.uniform(50, 70)
            demands['mMTC'] = self.rng.uniform(8, 12)
        elif current_scenario == 'full_congestion':
            demands['eMBB'] = self.rng.uniform(60, 80)
            demands['URLLC'] = self.rng.uniform(40, 60)
            demands['mMTC'] = self.rng.uniform(20, 35)
        else:
            demands['eMBB'] = self.rng.uniform(35, 45)
            demands['URLLC'] = self.rng.uniform(10, 15)
            demands['mMTC'] = self.rng.uniform(8, 12)

        for s_type in demands:
            demands[s_type] = max(0, demands[s_type] + self.rng.normal(0, 1.0))
            
        return demands
