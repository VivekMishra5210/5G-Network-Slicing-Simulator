# 5G Network Slicing Simulator: Architecture & Codebase Guide

This document explains exactly how the 5G Network Slicing Simulator works, the execution flow, and a detailed breakdown of what every single file in the project does.

---

## 1. The Global Project Flow (How it all works)

At its core, this project is a **Discrete-Time Simulator**. This means it runs in a loop, calculating what happens in the network second-by-second (Time Step $t=0, 1, 2...$).

Here is the flow of data from start to finish:

```mermaid
flowchart TD
    A[User / Dashboard Input] -->|Bandwidth, Scenario, Algorithm| B(main.py / app.py)
    B --> C[Simulator Initializes Network & Slices]
    
    subgraph Simulation Loop (Runs 60 times for 60 seconds)
        direction TB
        D[TrafficGenerator] -->|Generates random traffic| E[Update Slice Demands]
        E --> F[Allocator]
        F -->|Distributes Bandwidth| G[Slice calculates Latency & Packet Loss]
        G --> H[Check QoS against limits]
        H --> I[Save data to Slice History]
    end
    
    C --> Simulation Loop
    Simulation Loop --> J[Compile all History into a Pandas DataFrame]
    J --> K[metrics.py calculates Averages & QoS %]
    J --> L[plots.py draws Graphs]
    J --> M[Dashboard renders UI]
```

### The "Tick" (What happens in one second):
1. **Traffic Generation:** The `TrafficGenerator` rolls virtual dice (NumPy random) to decide how much data eMBB, URLLC, and mMTC users are asking for right now.
2. **Allocation:** The chosen algorithm (e.g., `QoSAllocator`) looks at the network's 100 Mbps and decides how much to give to each slice based on their demand and priority.
3. **Metrics Calculation:** The slices calculate their own performance. If demand > allocation, they record *packet loss*. If the network is congested, they calculate higher *latency*.
4. **QoS Check:** The slice checks if its metrics violated its requirements (e.g., did URLLC latency go over 5ms?). It records a `True` or `False`.
5. **History:** All these numbers are saved for this specific second, and the loop repeats.

---

## 2. Directory & File Deep Dive

Here is the exact purpose of every file in the codebase.

### ⚙️ Configuration
* **`config/config.py`**
  The master settings file. It defines the rules of the universe. It contains `TOTAL_BANDWIDTH` (100 Mbps), simulation length, and the `SLICE_CONFIG` dictionary which holds the strict rules for each slice (priority, min/max bandwidth, required latency, and required packet loss).

### 🏗️ Core Data Models
* **`models/user_model.py`**
  A simple class representing an individual user (e.g., a phone or an IoT sensor). Currently used to populate the slices.
* **`models/slice_model.py`** *(Crucial File)*
  The `NetworkSlice` class. This is the workhorse of the simulation. It holds its current demand, its allocated bandwidth, and contains the logic (`calculate_metrics`) to figure out its own latency and packet loss based on network load. It also saves its data every second into a `history` list.
* **`models/network_model.py`**
  The `Network` class. A container that holds the three slices together. It calculates global stats like total network demand and network load ratio.

### 🚦 Traffic Generation
* **`traffic/traffic_generator.py`**
  Acts like the real world. It looks at the current time step and the chosen scenario. If the scenario is "urllc_emergency", it forces URLLC demand to spike to 50-70 Mbps. It adds Gaussian noise (slight randomness) so the graphs look jagged and realistic, not flat.

### 🧠 The Brains (Algorithms)
* **`allocation/static_allocator.py`**
  The "Dumb" algorithm. It ignores what the slices actually need and always gives exactly 50% to eMBB, 30% to URLLC, and 20% to mMTC.
* **`allocation/round_robin.py`**
  The "Fair" algorithm. It gives everyone their minimum bandwidth, then splits the remaining bandwidth perfectly equally among whoever needs more. It doesn't care if URLLC is an emergency and eMBB is just Netflix.
* **`allocation/qos_allocator.py`** *(Crucial File)*
  The "Smart" algorithm. It gives minimums, then calculates a `priority_score` for each slice. If a slice's QoS failed in the previous second, its score gets a massive +5 boost. It then distributes remaining bandwidth mathematically proportional to these scores.

### 🕹️ Simulation Engine & Scenarios
* **`simulation/scenarios.py`**
  A simple dictionary defining the 5 scenarios (Normal, Heavy eMBB, URLLC Emergency, Full Congestion, Dynamic).
* **`simulation/simulator.py`** *(Crucial File)*
  The Orchestra Conductor. It imports everything above. Its `run()` method contains the main `for time_step in range(duration):` loop. After the loop finishes, it converts all the slice histories into a massive, easy-to-read Pandas `DataFrame` (a spreadsheet).

### 📊 Data Processing & Visualization
* **`metrics/metrics.py`**
  Takes the history of the simulation and calculates the final grades: Average Throughput, Average Latency, and the ultimate metric: **QoS Satisfaction %** (what percentage of the time did the slice stay within its required limits).
* **`visualization/plots.py`**
  Takes the Pandas DataFrame and uses `matplotlib` to draw line charts, bar charts, and stacked area charts. It saves them as `.png` images in the `results/graphs/` folder.

### 💻 The User Interface
* **`dashboard/app.py`**
  A Flask web server. It creates the `/api/simulate` endpoint. When the website asks for a simulation, this file translates the web request, runs the Python simulator, and sends the Pandas DataFrame back to the website as JSON data.
* **`dashboard/templates/index.html`**
  The Frontend. A single file containing HTML, CSS (for the cool dark glassmorphism look), and JavaScript. It grabs data from `app.py` and uses `Chart.js` to draw interactive graphs directly in the browser.

### 🚀 Entry Points
* **`experiments/run_experiments.py`**
  A brute-force testing script. It runs every algorithm against every scenario (15 simulations total), saves all the data to CSVs, and generates all the comparison plots for your final report.
* **`main.py`**
  The main door to the project. You use it in the terminal to either run a specific simulation (`python main.py --scenario dynamic`) or start the web server (`python main.py --dashboard`).
