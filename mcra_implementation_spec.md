# Streamlined Agent Implementation Brief: Research-Grounded MCRA Simulation

> **Repository:** `5G-Network-Slicing-Simulator` ([GitHub](https://github.com/VivekMishra5210/5G-Network-Slicing-Simulator))  
> **Primary Reference:** Jia-You Lin et al., "Dynamic Resource Allocation for Network Slicing with Multi-Tenants in 5G Two-Tier Networks," *Sensors*, 23(10), 4698 (2023), [DOI:10.3390/s23104698](https://doi.org/10.3390/s23104698).  
> **Goal:** Implement an **isolated, additive MCRA simulation mode** alongside existing algorithms without modifying or breaking legacy code.

---

## 0. Non-Negotiable Constraints
1. **Strict Isolation:** Do not delete, rename, refactor, or alter existing algorithms (`Static`, `Round-Robin`, `QoS-Adaptive`), routes, or schemas. Add MCRA as an additive feature/route option.
2. **Deterministic & Log-Driven:** Keep runs deterministic for fixed seeds. All dashboard metrics must derive directly from actual simulation event logs (no hard-coded or fake results).
3. **Research Fidelity (Educational Adaptation):** Adapt the paper's core iterative marginal-cost resource allocation, capacity limits, latency constraints, and admission/blocking rules.

---

## 1. Architecture & File Layout

Add an isolated `mcra/` package and integration hooks:
```text
project-root/
├── app.py                          # Minimal additive wiring for MCRA route/API
├── allocators/mcra_allocator.py    # MCRA cost and allocation logic
├── mcra/
│   ├── __init__.py
│   ├── models.py                   # Packet, Request, Link, ComputeNode, Route, Events
│   ├── topology.py                 # Graph & candidate paths (Edge/Cloud/Hybrid)
│   ├── traffic.py                  # Reproducible request generators (eMBB, URLLC, mMTC)
│   ├── event_engine.py             # Discrete-event priority queue (time, sequence)
│   ├── queues.py                   # Link/compute queues & service discipline
│   ├── resources.py                # Resource ledger (atomic reservation/release)
│   ├── latency.py                  # E2E delay components (queue, serialization, propagation, compute)
│   ├── allocator.py                # MCRA marginal-cost iterative loop facade
│   ├── metrics.py                  # Request, packet, resource, and QoS metrics
│   └── simulation.py               # Main MCRA orchestration loop
├── templates/index.html            # Minimal additive MCRA selector & results view
└── tests/test_mcra_*.py            # Comprehensive unit and regression tests
```

---

## 2. Core MCRA Algorithm Contract

### Marginal Cost Function
The cost of adding resource increments increases convexly with node resource occupancy. Implement a clean, unit-tested function based on the paper's exponential cost model:
* **Cost Equation Shape:** $C(u) = \delta^{(u/M - 1)}$ where $u$ is usage, $M$ is capacity, and $\delta$ is the cost base (`cost_base > 1`).
* **Marginal Cost of Increment $\Delta u$:** $\gamma(u, \Delta u, M) = C(u + \Delta u) - C(u)$.

### Iterative Allocation Loop (`admit_request_mcra`)
1. **Initial Trial:** Start the request on a candidate path with minimum initial resource allocations. Compute predicted E2E delay.
2. **Feasibility Check:** If predicted delay $\le$ deadline and resources are available, reserve atomically and **ACCEPT**.
3. **Refinement Loop:** If delay exceeds the deadline, evaluate eligible resource nodes/links on the path. Calculate the marginal cost for a legal unit increment on each.
4. **Lowest-Cost Increment:** Select the legal increment with the **minimum marginal cost**, apply it to the tentative plan, and recompute delay.
5. **Termination:** 
   * If delay $\le$ deadline and capacity allows $\rightarrow$ **ACCEPT** (commit atomically).
   * If capacity is exhausted or iteration limits are reached $\rightarrow$ **BLOCK** with a structured reason code (`BLOCKED_CAPACITY`, `BLOCKED_QOS_UNSATISFIABLE`, etc.).
6. **Rollback:** Failed tentative plans must never leak reservations.

---

## 3. Network Entities & Packet Flow

* **Topology:** Explicit graph containing Traffic Sources/UEs $\rightarrow$ Access Link $\rightarrow$ Edge Router/gNB $\rightarrow$ [MEC Edge Node / Core Backhaul Link $\rightarrow$ Cloud Node] $\rightarrow$ Destination.
* **Slices:** eMBB (large payloads, throughput/burst focused), URLLC (strict latency budgets, low drop tolerance), mMTC (sensor bursts, periodic/jittered arrivals).
* **E2E Delay Formula:** 
  $$D_{E2E} = D_{queue} + D_{serialization} + D_{propagation} + D_{compute}$$
  * *Serialization:* Payload bits divided by effective link bit rate ($1 \text{ Mbps} = 1,000 \text{ bits/ms}$).
* **Discrete-Event Engine:** Priority queue ordered by `(time_ms, sequence)`. Tracks events: `REQUEST_ARRIVAL`, `LINK_SERVICE_COMPLETED`, `COMPUTE_SERVICE_COMPLETED`, `RESOURCE_RELEASED`, `QUEUE_OVERFLOW_DROP`.

---

## 4. Single-Shot Execution Plan for the Agent

Execute the implementation in four streamlined phases:

1. **Phase 1: Core Models & Ledger (`mcra/models.py`, `resources.py`, `latency.py`)**
   * Build immutable dataclasses for requests, packets, links, compute nodes, and events.
   * Implement atomic resource ledger with zero-negative check and single-release guarantees.
   * Implement unit-tested E2E delay calculation and unit conversions.

2. **Phase 2: Event Engine & Traffic (`mcra/event_engine.py`, `traffic.py`, `queues.py`)**
   * Build deterministic discrete-event scheduler.
   * Implement reproducible traffic generators for eMBB, URLLC, and mMTC profiles.
   * Implement FIFO/priority queueing and drop tracking.

3. **Phase 3: MCRA Allocator & Topology (`allocators/mcra_allocator.py`, `mcra/simulation.py`)**
   * Implement the verified marginal cost calculation and iterative increment loop.
   * Wire up admission control, atomic commits, rollbacks, and reason codes.
   * Orchestrate full simulation runs across edge-only, cloud-only, and hybrid topologies.

4. **Phase 4: API, UI & Regression Tests (`app.py`, templates, `tests/`)**
   * Expose MCRA via an isolated API endpoint/mode without breaking legacy routes.
   * Add dashboard UI components for topology visualization, decision inspection, and timeline replay.
   * Write comprehensive unit tests for marginal cost, ledger invariants, and regression tests ensuring legacy algorithms remain untouched.

---

## 5. Acceptance Criteria Checklist
* [ ] Marginal cost and delay calculations pass unit tests.
* [ ] Tentative allocations properly roll back on failure.
* [ ] Event engine runs deterministically with a fixed seed.
* [ ] Legacy endpoints and algorithms (`Static`, `Round-Robin`, `QoS-Adaptive`) remain 100% unchanged and pass regression tests.
* [ ] Dashboard successfully executes MCRA runs and displays actual event-driven metrics, request logs, and decision traces.