# Module Documentation: `metrics/`

## 1. Overview
The `metrics/` module calculates high-level statistical aggregations and Service Level Agreement (SLA) satisfaction rates across simulation runs. It provides functions to evaluate and compare algorithm performance.

---

## 2. File Deep-Dive: `metrics/metrics.py`

### 2.1. Functions Breakdown

#### 1. `calculate_qos_satisfaction(history_list)`
Calculates the percentage of time steps in which a slice successfully satisfied all QoS SLA criteria (both latency and packet loss):
$$\text{QoS Satisfaction Rate} = \left( \frac{\sum_{t=1}^{T} \mathbb{I}(\text{qos\_satisfied}_t == \text{True})}{T} \right) \times 100$$
*   **Input:** `history_list` (*list[dict]*): Array of step records from a slice.
*   **Returns:** *float* percentage between `0.0` and `100.0%`.

#### 2. `calculate_avg_throughput(history_list)`
Computes the mean delivered data rate over the entire simulation duration:
$$\bar{\Theta} = \frac{1}{T} \sum_{t=1}^{T} \Theta(t)$$
*   **Returns:** *float* average throughput in Mbps.

#### 3. `calculate_avg_latency(history_list)`
Computes the temporal average end-to-end delay:
$$\bar{\Lambda} = \frac{1}{T} \sum_{t=1}^{T} \Lambda(t)$$
*   **Returns:** *float* average latency in ms.

#### 4. `calculate_avg_packet_loss(history_list)`
Computes the average packet loss percentage:
$$\bar{L} = \frac{1}{T} \sum_{t=1}^{T} L(t)$$
*   **Returns:** *float* average packet loss in %.

#### 5. `generate_summary(data_source, algorithm_name=None, scenario_name=None)`
A polymorphic aggregator capable of processing either:
1.  **A pandas DataFrame:** Groups by `algorithm` and `slice` to produce a nested summary dictionary of all averages and QoS satisfaction rates.
2.  **A Network Object:** Inspects `network.slices` directly and compiles summary statistics from in-memory histories.

---

## 3. Output Schema & Summary Structure

```json
{
  "Static": {
    "eMBB": {
      "avg_throughput": 42.67,
      "avg_latency": 27.20,
      "avg_packet_loss": 12.90,
      "qos_satisfaction": 66.7
    },
    "URLLC": {
      "avg_throughput": 15.78,
      "avg_latency": 5.99,
      "avg_packet_loss": 7.86,
      "qos_satisfaction": 50.0
    },
    "mMTC": {
      "avg_throughput": 10.39,
      "avg_latency": 52.26,
      "avg_packet_loss": 0.00,
      "qos_satisfaction": 100.0
    }
  },
  "QoS Adaptive": {
    "URLLC": {
      "avg_throughput": 19.11,
      "avg_latency": 5.35,
      "avg_packet_loss": 1.98,
      "qos_satisfaction": 50.0
    }
  }
}
```

---

## 4. Viva / Defense Preparation Questions
1. **Q:** *Why is QoS Satisfaction % a better metric than just average latency or average throughput?*
   * **A:** Average latency can mask severe intermittent failures. For example, if URLLC latency is 2 ms for 50 seconds but spikes to 30 ms for 10 seconds, the average latency might look acceptable (~6.6 ms), but the autonomous vehicle would have crashed during those 10 seconds. QoS Satisfaction % measures SLA availability over time.
2. **Q:** *How is this metric used by the Dashboard?*
   * **A:** `dashboard/app.py` invokes `generate_summary()` to populate the live status cards and algorithm comparison tables.
