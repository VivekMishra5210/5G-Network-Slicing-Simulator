# Module Documentation: `simulation/`

## 1. Overview
The `simulation/` module orchestrates the discrete-event lifecycle of the virtual 5G network. It binds data models, traffic generation, scheduling algorithms, and metric recording into a unified simulation framework.

---

## 2. File Deep-Dive

### 2.1. `simulation/scenarios.py`

#### Purpose
Defines the metadata catalog for all supported operational simulation scenarios.

```python
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
```

---

### 2.2. `simulation/simulator.py` — `Simulator` Class

#### Purpose
The master execution engine. Coordinates time steps, manages allocator execution, and converts slice history logs into structured pandas DataFrames.

#### Constructor Parameters
```python
def __init__(self, total_bandwidth=None, duration=None, seed=42):
```
*   `total_bandwidth` (*float*): Network capacity in Mbps (defaults to `100`).
*   `duration` (*int*): Total simulation duration in seconds (defaults to `60`).
*   `seed` (*int*): Random seed passed to the stochastic traffic generator.

---

## 3. Core Methods & Simulation Lifecycle

### 3.1. Method: `_setup_network(self)`
1.  Instantiates a new `Network(total_bandwidth)`.
2.  Iterates through `SLICE_CONFIG` to construct three `NetworkSlice` objects (`eMBB`, `URLLC`, `mMTC`).
3.  Populates each slice with `base_users` number of `User` instances.
4.  Attaches slices to the network instance and returns it.

### 3.2. Method: `run(self, scenario_name='normal', allocator=None)`
Executes the discrete-time simulation loop:

```mermaid
flowchart TD
    Init[1. Initialize Network & Traffic Generator] --> LoopStart[2. Enter Time Loop: t = 0 to duration-1]
    
    LoopStart --> ResetInstant[a. Clear instantaneous allocations<br>Preserve previous qos_satisfied state]
    ResetInstant --> GenTraffic[b. TrafficGenerator generates demands for t]
    GenTraffic --> UpdateDemands[c. Set slice.current_demand for each slice]
    UpdateDemands --> ExecAlloc[d. Call allocator.allocate(network)]
    ExecAlloc --> LoadRatio[e. Compute network load ratio]
    LoadRatio --> CalcMetrics[f. For each slice: calculate_metrics & check_qos]
    CalcMetrics --> RecordHist[g. slice.record_step(t) & append to results list]
    
    RecordHist --> CheckDone{t == duration - 1?}
    CheckDone -->|No| NextTick[t = t + 1] --> LoopStart
    CheckDone -->|Yes| FormatDF[3. pd.DataFrame(results)]
    FormatDF --> ReturnDF[Return results DataFrame]
```

#### DataFrame Output Schema
The returned pandas DataFrame contains the following columns for every time step and every slice:
*   `time` (*int*): Time step second ($0$ to $59$).
*   `algorithm` (*str*): Allocator name (`'Static'`, `'Round Robin'`, `'QoS Adaptive'`).
*   `scenario` (*str*): Scenario executed.
*   `slice` (*str*): Slice identifier (`'eMBB'`, `'URLLC'`, `'mMTC'`).
*   `demand` (*float*): Instantaneous data rate requested (Mbps).
*   `allocation` (*float*): Bandwidth assigned (Mbps).
*   `throughput` (*float*): Actual data delivered (Mbps).
*   `latency` (*float*): Delay measured (ms).
*   `packet_loss` (*float*): Dropped packet percentage (%).
*   `utilization` (*float*): Slice allocation as percentage of total 100 Mbps network capacity.
*   `qos_satisfied` (*bool*): `True` if within SLA, `False` if violated.

### 3.3. Method: `run_all_algorithms(self, scenario_name='normal')`
Executes `run()` three times using `StaticAllocator()`, `RoundRobinAllocator()`, and `QoSAllocator()` under the same traffic seed, and concatenates all records into one comparative DataFrame.

### 3.4. Method: `run_all_experiments(self)`
Iterates through all 5 scenarios defined in `SCENARIOS`, running `run_all_algorithms()` on each, generating a complete 15-experiment dataset.

---

## 4. Viva / Defense Preparation Questions
1. **Q:** *Why is `qos_satisfied` preserved across time steps instead of reset to True at the start of each second?*
   * **A:** To enable closed-loop adaptive feedback. The QoS Adaptive allocator needs to know if a slice suffered an SLA violation in the *previous* second ($t-1$) so it can immediately apply the $+5.0$ priority escalation penalty at the *current* second ($t$) to recover the slice.
2. **Q:** *What is the advantage of converting slice histories to a pandas DataFrame?*
   * **A:** A standardized DataFrame enables vectorized grouping, filtering, CSV export, matplotlib visualization, and easy conversion to JSON for the web dashboard.
