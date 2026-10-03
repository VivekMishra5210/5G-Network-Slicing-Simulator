# Module Documentation: `allocation/`

## 1. Overview
The `allocation/` module contains the resource-scheduling intelligence of the 5G network simulator. It implements three distinct allocation paradigms:
1. **Static Allocation (`static_allocator.py`):** Fixed ratio resource isolation baseline.
2. **Round Robin Allocation (`round_robin.py`):** Fair-share iterative allocation with minimum reservations.
3. **QoS-Aware Adaptive Allocation (`qos_allocator.py`):** Dynamic priority and SLA-feedback-driven allocation with starvation prevention.

---

## 2. File Deep-Dive

### 2.1. `allocation/static_allocator.py` — `StaticAllocator` Class

#### Concept
The legacy baseline approach. Resources are rigidly segmented using pre-configured static percentages, regardless of actual real-time user traffic or SLA violations.

#### Algorithm Logic
For each slice $i$ in the network:
$$B_i(t) = C_{\text{total}} \times \text{ALLOCATION\_RATIOS}[i]$$
*   $B_{\text{eMBB}} = 100 \times 0.50 = 50\text{ Mbps}$
*   $B_{\text{URLLC}} = 100 \times 0.30 = 30\text{ Mbps}$
*   $B_{\text{mMTC}} = 100 \times 0.20 = 20\text{ Mbps}$

#### Weaknesses & Limitations
*   **Stranded Capacity:** If mMTC only demands 8 Mbps, 12 Mbps remains unused and wasted even if eMBB is suffering from severe packet loss.
*   **Emergency Inflexibility:** During a URLLC emergency ($D_{\text{URLLC}} = 65\text{ Mbps}$), URLLC is rigidly throttled to 30 Mbps, causing $>50\%$ packet loss and catastrophic latency breach.

---

### 2.2. `allocation/round_robin.py` — `RoundRobinAllocator` Class

#### Concept
A dynamic fair-sharing approach. Guaranteed minimum bandwidth is assigned first; then remaining capacity is split equally among slices with unmet demand.

#### Step-by-Step Algorithm:
1.  **Guaranteed Minimums:**
    $$B_i(t) = \min(B_i^{\text{min}}, B_i^{\text{max}})$$
    *Reserved Capacity:* $20\text{ (eMBB)} + 10\text{ (URLLC)} + 5\text{ (mMTC)} = 35\text{ Mbps}$.
2.  **Calculate Unreserved Remaining Capacity:**
    $$R = C_{\text{total}} - \sum_{i} B_i(t) = 100 - 35 = 65\text{ Mbps}$$
3.  **Iterative Fair Distribution Loop:**
    *   Find all needy slices: $\text{Needy} = \{ i \mid B_i(t) < \min(D_i(t), B_i^{\text{max}}) \}$.
    *   Compute equal slice share: $\text{share} = \frac{R}{|\text{Needy}|}$.
    *   For each needy slice, allocate:
        $$\Delta B_i = \min(\text{share}, \min(D_i, B_i^{\text{max}}) - B_i(t))$$
        $$B_i(t) \leftarrow B_i(t) + \Delta B_i, \quad R \leftarrow R - \Delta B_i$$
    *   Repeat until $R \le 0.01$ or $\text{Needy} = \emptyset$.

#### Advantages & Limitations
*   **Advantage:** Prevents stranded capacity; unused mMTC bandwidth is automatically reclaimed.
*   **Limitation:** "QoS-Blind". An eMBB user downloading video files is given the exact same slice of excess bandwidth as an autonomous vehicle transmitting safety telemetry.

---

### 2.3. `allocation/qos_allocator.py` — `QoSAllocator` Class

#### Concept
The core contribution of this project. Combines minimum reservation bounds, slice priority weighting, demand pressure, and closed-loop feedback from past QoS SLA violations to dynamically optimize bandwidth distribution.

```mermaid
flowchart TD
    Start[Start Allocation Step] --> MinAlloc[Step 1: Assign min_bandwidth to all slices<br>eMBB=20, URLLC=10, mMTC=5 Mbps]
    MinAlloc --> CalcRem[Step 2: Remaining Bandwidth R = 100 - 35 = 65 Mbps]
    CalcRem --> CalcScore[Step 3: Calculate Dynamic Priority Score S_i for each slice]
    
    subgraph Scoring Logic
        BasePrio[Base Priority: URLLC=5, eMBB=3, mMTC=2] --> AddDemand[+ Demand Factor: min 5.0, (Demand - Min)/Min * 2]
        AddDemand --> AddViolation[+ QoS Violation Penalty: +5.0 if previous qos_satisfied == False]
    end
    
    CalcScore --> ScoreReady[Score S_i computed for all slices]
    ScoreReady --> LoopStart[Step 4: Iterative Weighted Allocation Loop]
    
    LoopStart --> CheckNeedy{Needy slices exist & R > 0.01?}
    CheckNeedy -->|No| Done[Allocation Complete]
    CheckNeedy -->|Yes| WeightCalc[Compute Weights: W_i = S_i * D_i]
    WeightCalc --> ProportionalShare[Share = R * W_i / Total_Weight]
    ProportionalShare --> CapDeficit[Allocate: min share, Deficit to max_bw]
    CapDeficit --> UpdateRem[Update allocations & decrease R]
    UpdateRem --> CheckNeedy
```

#### Step-by-Step Mathematical Formulation

##### 1. Starvation Prevention (Minimum Reservations):
$$B_i^{(0)} = \min(B_i^{\text{min}}, B_i^{\text{max}})$$
$$\text{Remaining Bandwidth } R = C_{\text{total}} - \sum_i B_i^{(0)}$$

##### 2. Dynamic Priority Score Computation:
For each slice $i$:
$$S_i = \max(1.0, P_i^{\text{base}} + f_{\text{demand}}(i) + f_{\text{violation}}(i))$$
Where:
*   $P_{\text{URLLC}}^{\text{base}} = 5$, $P_{\text{eMBB}}^{\text{base}} = 3$, $P_{\text{mMTC}}^{\text{base}} = 2$.
*   $f_{\text{demand}}(i) = \min\left(5.0, \frac{D_i - B_i^{\text{min}}}{B_i^{\text{min}}} \times 2.0\right)$ if $D_i > B_i^{\text{min}}$, else $0$.
*   $f_{\text{violation}}(i) = 5.0$ if $\text{qos\_satisfied}_{t-1} == \text{False}$, else $0.0$.

##### 3. Iterative Weighted Share Allocation:
In each iteration, for active needy slices ($\text{Needy} = \{i \mid B_i < \min(D_i, B_i^{\text{max}})\}$):
$$\text{Total Weight } W_{\text{total}} = \sum_{k \in \text{Needy}} (S_k \times \max(1.0, D_k))$$
$$\text{Share}_i = R \times \left( \frac{S_i \times \max(1.0, D_i)}{W_{\text{total}}} \right)$$
$$\Delta B_i = \min\left(\text{Share}_i, \min(D_i, B_i^{\text{max}}) - B_i\right)$$
$$B_i \leftarrow B_i + \Delta B_i, \quad R \leftarrow R - \Delta B_i$$
Iterates until unallocated bandwidth $R < 0.01\text{ Mbps}$ or all demands/ceilings are fully met.

---

## 3. Comparative Matrix of Algorithms

| Feature | Static Allocator | Round Robin Allocator | QoS-Aware Adaptive Allocator |
|---|---|---|---|
| **Resource Efficiency** | Low (Stranded bandwidth) | High | High |
| **QoS Awareness** | None | None | High (Closed-loop feedback) |
| **Emergency Handling** | Fails (Rigid cap) | Partial (Equal share) | Superior (Priority escalation) |
| **Starvation Prevention** | Inherent (Fixed slice) | Inherent (Min guarantee) | Inherent (Min guarantee) |
| **Computational Complexity** | $O(1)$ | $O(N \cdot K)$ | $O(N \cdot K)$ |

*Where $N$ is the number of slices (3) and $K$ is the number of convergence iterations ($\le 20$).*

---

## 4. Viva / Defense Preparation Questions
1. **Q:** *Why multiply Priority Score by Demand ($S_i \times D_i$) in the weighting formula?*
   * **A:** If a slice has a high priority score (e.g., URLLC score = 12) but only requests 1 Mbps of traffic, allocating it 50% of the network based solely on score would over-allocate and waste bandwidth. Weighting by $S_i \times D_i$ aligns bandwidth distribution with actual volumetric urgency.
2. **Q:** *What happens when all slices violate QoS simultaneously (Full Congestion)?*
   * **A:** All slices receive the $+5.0$ violation boost. The base priority hierarchy ($5 > 3 > 2$) then re-asserts dominance, ensuring URLLC is protected first, followed by eMBB, while mMTC operates on its guaranteed minimum.
