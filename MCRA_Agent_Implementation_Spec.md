# Agent Implementation Brief: Research-Grounded MCRA + Packet-Flow 5G Network Slicing Simulator

> **Purpose:** Give an autonomous coding agent a precise, staged
> implementation plan for adding a research-grounded Minimum Cost
> Resource Allocation (MCRA) simulation to the existing
> `5G-Network-Slicing-Simulator` repository.
>
> **Repository:**
> https://github.com/VivekMishra5210/5G-Network-Slicing-Simulator\
> **Primary research reference:** Jia-You Lin, Ping-Hung Chou, and
> Ren-Hung Hwang, "Dynamic Resource Allocation for Network Slicing with
> Multi-Tenants in 5G Two-Tier Networks," *Sensors*, 23(10), 4698
> (2023), DOI: https://doi.org/10.3390/s23104698\
> **Research article:** https://www.mdpi.com/1424-8220/23/10/4698\
> **Important:** This document is an implementation specification, not
> permission to rewrite the existing simulator. Implement MCRA as an
> isolated, additive feature.

------------------------------------------------------------------------

## 0. Mission and non-negotiable constraints

Implement a new **MCRA-only simulation mode** that models individual
service requests/packets moving through a simplified but explicit 5G
edge/cloud network, with queues, link capacities, compute capacities,
end-to-end delay, QoS constraints, resource reservation/release, request
blocking, and a dynamic Minimum Cost Resource Allocation decision loop.

The existing project currently includes: - A Flask dashboard in
`app.py`. - A simulation engine (for example, `Simulator`). - Existing
`Static`, `Round-Robin`, and `QoS-Adaptive` allocation strategies. -
Three service/slice types: eMBB, URLLC, and mMTC. - Traffic scenarios
and metrics already used by the dashboard.

### Strict isolation rules

1.  **Do not delete, rename, refactor, or silently change the existing
    Static, Round-Robin, or QoS-Adaptive algorithms.**
2.  Do not change their default behavior, parameter defaults, results
    schema, routes, or metrics semantics.
3.  Add new MCRA modules/classes and an explicit MCRA route or algorithm
    option.
4.  If shared code must be reused, preserve backward compatibility and
    prove it with regression tests.
5.  Do not make existing comparisons claim that MCRA was evaluated by
    the old scalar-bandwidth model. MCRA's new topology and metrics must
    be clearly labeled.
6.  Keep the new simulator deterministic for a fixed seed.
7.  Never fabricate performance improvements or hard-code favorable
    results. All dashboard metrics must come from actual simulation
    event logs.
8.  Do not describe the implementation as a bit-accurate 5G NR
    physical-layer simulator. It is a packet/event-level network
    abstraction unless a real PHY/MAC model is actually implemented.

### Required outcome

A user should be able to choose **MCRA** in the dashboard and see: - A
topology view of UE/traffic sources, radio/access link, edge node,
core/backhaul link, cloud node, and destination. - Packets/requests
being generated, queued, routed, served, delayed, dropped, blocked, and
completed. - Why MCRA selected a particular resource node at each
allocation step. - Per-slice and overall QoS, latency, resource use,
blocking, packet delivery, and throughput. - An event log that explains
each decision in human-readable terms. - Exportable CSV/JSON results and
reproducible runs.

------------------------------------------------------------------------

## 1. Research fidelity: what MCRA means here

The paper proposes **Minimum Cost Resource Allocation (MCRA)** for
dynamic resource allocation and routing/offloading in a **two-tier,
multi-tenant network**. The main idea is not "give more bandwidth to the
highest-priority slice." When a service request fails its end-to-end
latency constraint, MCRA iteratively increases resource allocation in
small units, choosing the eligible node/resource whose **marginal
allocation cost is lowest**, while respecting that node's maximum
capacity. Resource allocation continues until the request meets its
latency requirement or no legal resource increase is possible. If the
resulting request cannot be supported with available resources, it is
blocked.

The paper models both: - **Communication resources** (links / transport
resources), and - **Computation resources** (edge/cloud processing
capacity).

The paper's MCRA marginal-cost expression is based on the increase in a
convex exponential cost as a node's allocated/occupied resource fraction
increases. In the paper's notation, the cost of adding one unit at node
(X) is:

\[ `\gamma`{=tex}\^X =
`\partial`{=tex}\^{`\left`{=tex}(`\frac{F_{i,l}^{X}+R_{i,j,l}^{X}+\alpha\mu_{i,j,l}^{X}}{MR_{i,l}^{X}}`{=tex}-1`\right`{=tex})} -
`\partial`{=tex}\^{`\left`{=tex}(`\frac{F_{i,l}^{X}+R_{i,j,l}^{X}}{MR_{i,l}^{X}}`{=tex}-1`\right`{=tex})}
\]

where the symbols represent the paper's node resource usage/reservation,
the current request's allocation, the maximum resource capacity, the
minimum resource unit, and a cost-base parameter. Consult the paper's
equations and Algorithm 3 directly before implementing; do not rely on
this short summary alone. The paper describes
(`\alpha`{=tex}`\mu`{=tex}) as a small allocation increment: for
computation resources, the example uses a unit increment of 1; for
communication resources, the example uses 0.1 times the minimum resource
unit. The implementation must document the exact mapping from paper
notation to code.

### Research-paper system model vs this project

The research paper's full model is richer than the current project. It
includes multiple tenants, three slices per tenant, edge/cloud nodes,
communication and compute resources, path routing/offloading, queuing
and end-to-end delay, and several network structures (Cloud-Only,
Edge-Only, Parallel Cloud-Edge Hybrid). The existing project currently
uses a much simpler scalar bandwidth pool and time-step model.

Implement a **clearly documented educational adaptation** of the paper's
MCRA idea, not a claim that the entire paper has been reproduced. The
adaptation must preserve the defining mechanism: iterative resource
increments, per-node capacity constraints, marginal cost evaluation,
lowest-cost feasible increment, recomputed latency, and
admission/blocking when QoS cannot be met.

### Paper-specific items to verify before coding

-   Exact definition and use of (F), (R), (MR), (`\mu`{=tex}),
    (`\alpha`{=tex}), and (`\partial`{=tex}).
-   Exact eligible node set for each topology model (CO, EO, PH).
-   Exact order of the checks in Algorithm 1 and Algorithm 3.
-   How E2E latency is calculated for communication and computation
    stages.
-   How the paper distinguishes per-request resource needs from
    remaining node capacity.
-   What the paper means by initial allocation and when a request is
    blocked.
-   Whether a particular parameter in the paper is a fixed constant or
    scenario-specific.
-   Use the published pseudocode and equations as the source of truth.
    If the implementation deliberately simplifies something, document
    the simplification in the README and in the dashboard's "Model
    assumptions" section.

------------------------------------------------------------------------

## 2. Scope of the network to simulate

Build an explicit, inspectable topology. The minimum useful topology is:

``` text
Traffic Sources / UEs
        |
        v
  Radio / Access Link
        |
        v
   Edge Router / gNB
        |
        +--------------------------+
        |                          |
        v                          v
   MEC / Edge Node          Core / Backhaul Link
        |                          |
        |                          v
        |                     Cloud Node
        |                          |
        +------------+-------------+
                     |
                     v
             Destination / Sink
```

This is a conceptual topology for an educational simulator. Avoid
implying that a single edge router is a literal complete 5G RAN/core
deployment.

### Required network entities

1.  **UE / TrafficSource**
    -   Unique ID, slice type, tenant ID (if multi-tenancy is enabled),
        traffic/application profile.
    -   Generates requests according to a reproducible arrival process.
    -   Each request carries payload size, arrival time,
        deadline/latency budget, required service rate or processing
        demand, and request ID.
2.  **Slice**
    -   Slice ID and type: eMBB, URLLC, or mMTC.
    -   QoS profile: latency budget, target delivery/reliability proxy,
        minimum service resources, optional priority.
    -   Must not be represented by a single "priority number" alone. QoS
        constraints are distinct.
3.  **CommunicationLink**
    -   Link ID, endpoints, capacity (Mbps), propagation delay (ms),
        current reserved/used bandwidth, optional queue capacity.
    -   Can be busy or congested; has a clear rule for queueing and
        service.
    -   Every request's route references actual links, so link usage can
        be accounted for.
4.  **ComputeNode**
    -   Node ID, tier (`edge` or `cloud`), processing capacity (e.g. CPU
        units/s or normalized compute units), base processing delay,
        current reserved/used compute, maximum capacity.
    -   Edge and cloud should have different capacities and delay
        assumptions. These are configurable teaching assumptions, not
        universal 5G constants.
5.  **Route / Path**
    -   Ordered list of links and processing nodes.
    -   Each route must be valid in the topology graph.
    -   At minimum support edge execution, cloud execution, and a
        hybrid/offload route where appropriate.
6.  **Packet / ServiceRequest**
    -   `request_id`, `tenant_id`, `ue_id`, `slice_type`,
        `arrival_time_ms`, `payload_bits` or `payload_bytes`,
        `compute_demand`, `deadline_ms`, `route_candidate`, `status`.
    -   Maintain a clear distinction between an application-level
        request and packets used to visualize its transfer. If a request
        is segmented into packets, track parent request ID and packet
        sequence.
    -   For a first implementation, one service request may be
        represented as a packetized flow; do not mix packet-level and
        request-level metrics without labels.
7.  **Queue**
    -   A queue belongs to a link or compute node.
    -   Has explicit discipline (e.g. per-slice FIFO or
        deadline/priority-aware, configurable and stated).
    -   Tracks enqueue/dequeue time, queue length, waiting time, and
        overflow drops.
    -   MCRA resource allocation and packet scheduling are related but
        not identical: document which component chooses resource
        reservations and which component orders packets.
8.  **Event Scheduler**
    -   Priority queue of discrete events ordered by
        `(time, stable_sequence_number)`.
    -   Events include arrival, enqueue, service start, service
        completion, link transmission completion, compute completion,
        timeout/deadline expiry, resource release, and drop/block.
    -   No reliance on arbitrary sleeps or real wall-clock timing. The
        simulation clock advances to the next event.
9.  **Resource ledger**
    -   Single source of truth for capacity, reservation, release, and
        current usage for each node/link.
    -   Prevent negative remaining capacity and double release.
    -   Every accepted allocation has an allocation record; every
        release refers to that record.
10. **MCRA allocator**
    -   Receives a request, candidate route(s), current network state,
        QoS budget, resource capacities, and the cost parameters.
    -   Produces an allocation plan, selected path/processing placement,
        per-resource increments, predicted latency, and a decision
        explanation.
    -   It must not directly manipulate Flask responses or UI state.

------------------------------------------------------------------------

## 3. Architecture and file layout

First inspect the actual repository and map this proposal onto its
existing naming conventions. Do not blindly create duplicate modules if
equivalent abstractions already exist.

Preferred additive structure (adjust to the real repo after inspection):

``` text
project-root/
├── app.py                         # Existing Flask app; minimal additive wiring only
├── simulator.py / existing engine # Existing engine, unchanged for legacy modes
├── allocators/                     # Or existing allocator module layout
│   └── mcra_allocator.py           # New MCRA cost/increment logic
├── mcra/
│   ├── __init__.py
│   ├── models.py                   # Packet, Request, Link, ComputeNode, Route, events
│   ├── topology.py                 # Graph and candidate paths
│   ├── traffic.py                  # MCRA traffic/request generation
│   ├── event_engine.py              # Discrete-event event queue
│   ├── queues.py                   # Link/compute queues and service discipline
│   ├── resources.py                # Resource ledger and reservation/release
│   ├── latency.py                  # Serialization, propagation, queue, compute, total E2E
│   ├── allocator.py                # MCRA loop; thin facade around marginal cost
│   ├── metrics.py                  # Packet/request and per-slice metrics
│   ├── simulation.py               # Orchestrates MCRA-only simulation
│   └── serialization.py            # JSON-safe output and CSV row conversion
├── templates/
│   └── index.html                  # Minimal additive MCRA selector/results area
├── static/                         # Existing dashboard assets, if present
├── tests/
│   ├── test_mcra_cost.py
│   ├── test_mcra_capacity.py
│   ├── test_mcra_latency.py
│   ├── test_mcra_events.py
│   ├── test_mcra_admission.py
│   ├── test_mcra_reproducibility.py
│   └── test_legacy_regression.py
├── results/mcra/                   # Optional generated output directory; don't commit random runs
└── docs/MCRA_MODEL.md              # Model, equations, assumptions, limitations
```

### Dependency direction

-   `models`, `resources`, `topology`, `latency`, and `queues` must not
    import Flask.
-   `mcra/allocator.py` depends on models/resources/topology/latency and
    cost calculation.
-   `mcra/simulation.py` orchestrates traffic, events, allocation,
    metrics.
-   `app.py` only validates input, invokes the MCRA simulation, and
    serializes results.
-   UI code only renders results returned by the simulation.
-   Avoid circular imports and giant single-file implementations.

------------------------------------------------------------------------

## 4. Model time and units explicitly

Choose and enforce a unit system. Recommended: - Simulation clock:
milliseconds (ms), floating-point or integer microseconds if
necessary. - Packet size: bits. - Link capacity: megabits per second
(Mbps), converted consistently to bits/ms. - Processing capacity:
normalized compute units per ms or tasks/s, but use one convention
everywhere. - Latency budget and propagation/queue/processing delay:
ms. - Compute demand: normalized compute units or CPU cycles; do not mix
CPU cycles and arbitrary units without a conversion model.

Conversion sanity check: - 1 Mbps = 1,000 bits/ms. - Serialization delay
(ms) = packet size (bits) / link rate (bits/ms). - For a link rate
`rate_mbps`, `bits_per_ms = rate_mbps * 1000`. -
`serialization_ms = packet_bits / (rate_mbps * 1000)`.

Document every unit in model classes and API parameters. Add tests for
conversions to prevent factor-of-1000 errors.

### Avoid fake precision

Use configurable model parameters and label them as simulation
assumptions. Do not claim that selected link rates, compute capacities,
propagation delays, packet sizes, or traffic rates are measured telecom
operator data unless an actual cited dataset is used.

------------------------------------------------------------------------

## 5. Traffic generation: model real workloads, not just random bandwidth

Build traffic as **request arrivals over time**. Each request should
have a source, slice, size, compute demand (where applicable), arrival
time, and QoS deadline.

### Required profiles

Use configurable distributions and deterministic random generators: -
**eMBB:** larger packets/flows, sustained or bursty high data rate,
examples such as video segments or broadband transfers. Use a
configurable mixture of large payload sizes and a burst model rather
than drawing every packet from a uniform distribution. - **URLLC:**
small or moderate payloads, strict latency deadline, low tolerance for
delay and drops; optionally create emergency bursts. - **mMTC:** many
small sensor reports, many UE/device identities, periodic or jittered
arrivals, potentially synchronized reporting bursts.

Do not set a traffic class's arrival rate equal to its bandwidth demand
without a clear derivation. Keep arrival rate, payload size, processing
demand, and offered bit rate separate.

### Traffic scenarios

Preserve current legacy scenarios exactly. Add MCRA-specific scenarios
or reuse names only if their definitions are clearly separated: 1.
`normal_mix`: baseline mixed eMBB/URLLC/mMTC traffic. 2. `embb_surge`:
video/download burst; high eMBB offered load. 3. `urllc_emergency`:
burst of latency-critical packets. 4. `mmtc_surge`: many IoT devices
reporting together. 5. `edge_overload`: edge compute saturation while
cloud remains available. 6. `backhaul_congestion`: core/backhaul link
bottleneck. 7. `mixed_peak`: simultaneous elevated load across slices.
8. `dynamic_day`: phases change during one run, with explicit
timestamps.

For each scenario, record its distributions and parameters in a
configuration object. Seed all RNGs. Do not regenerate a different
request trace for each algorithm if a later comparative experiment is
added.

### Request fields

At minimum: - IDs: request, UE, tenant, slice. - Arrival timestamp. -
Payload size in bits. - Required compute demand. - Deadline / maximum
end-to-end delay. - Application/traffic profile label. - Selected route,
if assigned. - Current status and status reason. - Predicted delay at
admission. - Actual completion time, end-to-end delay, and deadline
outcome. - Resource reservation IDs.

------------------------------------------------------------------------

## 6. Packet travel and end-to-end delay

The dashboard must visualize actual event data, not a decorative
animation disconnected from the simulator.

For each packet/request, calculate components separately:

\[ D\_{E2E} = D\_{queue} + D\_{serialization} + D\_{propagation} +
D\_{compute} + D\_{other} \]

Where: - **Queue delay:** time waiting before a link/node starts serving
the packet. - **Serialization/transmission delay:** payload bits divided
by effective link bit rate. - **Propagation delay:** configured
physical/link delay. - **Compute delay:** processing demand divided by
effective compute service rate, plus any configured fixed processing
delay. - **Other delay:** only explicit documented overheads, such as a
modeled forwarding delay. Keep it zero if not modeled.

For a multi-hop path, sum queue, serialization, and propagation delay
across each traversed link and compute delay at each processing node. Do
not count the same queue delay twice.

### Link capacity and congestion

-   A link has finite capacity and a defined service model.
-   Link capacity is not merely a metric displayed on the UI; it affects
    serialization/service completion time and admission/resource
    decisions.
-   If bandwidth is reserved dynamically, the effective rate used for
    latency prediction must be tied to that reservation in a documented
    way.
-   Track link utilization over time as used/reserved capacity divided
    by capacity, bounded to 0--100% for valid reservations.
-   If the queue has a finite buffer, overflow must create a real drop
    event with a reason. If the buffer is unbounded, label that
    simplification explicitly.

### Queueing

-   Choose a deterministic, testable queue discipline. Recommended
    initial choice: FIFO within each link and compute node, with
    slice-specific queues only if the scheduler logic is explicitly
    implemented.
-   If priority/deadline scheduling is used, make it configurable and
    state the tie-breaking rules. Do not claim MCRA itself is a packet
    scheduling algorithm.
-   Distinguish packet **queueing** from a service request being
    **blocked at admission**.

### Packetization

If a service request has a payload larger than the configured maximum
packet size: - Split it into packets with `parent_request_id`, sequence
number, and packet count. - Decide whether the full request completes
only when all packets arrive; implement that rule consistently. -
Request-level deadline success should be based on the defined completion
event, not whichever packet finishes first. - Do not count packet
fragments as separate application requests in blocking probability.

### Actual vs predicted latency

-   MCRA needs a latency estimate to decide whether more resources are
    needed.
-   The simulator also has actual event-driven latency from queue and
    service events.
-   Store both `predicted_e2e_delay_ms` and `actual_e2e_delay_ms`.
-   Explain differences caused by queueing, concurrent arrivals, and
    model approximations.
-   Never use actual future completion information to make a decision at
    arrival time.

------------------------------------------------------------------------

## 7. MCRA algorithm: exact behavioral contract

Implement MCRA as a **resource increment loop** based on the research
paper's marginal cost, not a static score ranking.

### Inputs

-   Incoming request `r`.
-   Candidate topology model/path options (at minimum edge, cloud, and
    hybrid where implemented).
-   Current node/link resource occupancy and maximum capacity.
-   Initial/minimum resource allocation per resource type.
-   QoS deadline `D_max(r)`.
-   Cost base `delta > 1` (use a documented configurable name such as
    `cost_base`; do not call it `delta` if that conflicts with existing
    project variables).
-   Resource increment sizes for compute and communication.
-   Resource usage/reservation accounting.
-   Latency estimator that uses current allocations and topology.

### Conceptual pseudocode

This is an implementation outline, not a substitute for checking the
paper's full Algorithm 1 and Algorithm 3.

``` text
function admit_request_mcra(request, topology_state):
    candidates = build_legal_candidate_plans(request, topology_state)

    for each candidate plan:
        allocate only the documented minimum initial resource units
        predicted_delay = estimate_e2e_delay(request, candidate, current_state)

        if predicted_delay <= request.deadline:
            compute the remaining resource requirement using the paper's prescribed model
            if every required resource is available:
                reserve resources atomically
                return ACCEPTED with path, allocation, delay, explanation
            else:
                continue to another legal candidate if policy permits

    choose the candidate/plan to refine according to the selected topology model
    while predicted_delay > request.deadline:
        eligible_resources = resources on the candidate path with remaining capacity

        for each eligible resource X:
            calculate the marginal cost of adding exactly one legal increment to X
            reject X if increment exceeds node/link maximum capacity
            compute candidate delay after this increment

        if no eligible increment can be applied:
            return BLOCKED with reason "capacity exhausted before QoS could be met"

        select the legal increment with minimum marginal cost
        apply it to the tentative plan only
        recompute end-to-end delay and cost state

        if iteration/resource limit is exceeded:
            return BLOCKED with reason "allocation search limit reached"
            # The limit must be configurable and visible; it is not a substitute for capacity checks.

    compute the full resource requirement using the model's rules
    if all required resources are available:
        atomically reserve resources
        return ACCEPTED with full decision trace
    else:
        return BLOCKED with reason "required resources unavailable"
```

### Critical correctness requirements

1.  **Read the complete paper pseudocode and equations first.** Preserve
    its ordering and topology-specific node sets where possible.
2.  Keep **tentative allocation** separate from committed resource
    state. A failed plan must not leak reservations.
3.  Recompute the marginal cost after each increment because the cost
    changes with occupancy.
4.  Recompute predicted end-to-end delay after each increment because
    resource changes affect service rate/delay.
5.  Respect each resource's maximum capacity and the system's remaining
    capacity.
6.  Never allocate negative resources, exceed capacities, or reserve the
    same resource twice for one step.
7.  Use a stable tie-breaker for equal costs (for reproducibility),
    e.g. resource type then node ID.
8.  If the selected path includes multiple links and a compute node,
    calculate cost per eligible resource and apply the exact defined
    update to one resource at a time.
9.  Define whether MCRA chooses among paths first or increments
    resources on a given candidate path first. Match the paper's
    topology-specific flow where possible; otherwise document a
    deterministic adaptation.
10. On acceptance, commit all reservations atomically. On block/failure,
    roll back every tentative allocation.
11. Resource release must occur when the associated service has actually
    completed (or been cancelled/expired according to the explicit
    model).
12. The algorithm must emit an auditable decision trace for every step.
13. The allocation loop must terminate under all inputs, including zero
    capacity, impossible QoS, and malformed demand.
14. MCRA is not simply "pick the least-utilized node"; marginal cost is
    the **incremental cost** of adding a resource unit under the chosen
    cost function.

### Marginal cost implementation

Implement a pure function with tests, e.g.:

``` python
def marginal_cost(
    used_before: float,
    increment: float,
    capacity: float,
    cost_base: float,
) -> float:
    ...
```

Map `used_before` to the exact paper terms only after verifying the
notation. The paper's cost uses the difference between exponential cost
at the post-increment and pre-increment normalized resource usage. A
generalized implementation shape is:

\[ C(u) = `\delta`{=tex}\^{(u/M - 1)} \] \[ `\gamma`{=tex}(u,
`\Delta `{=tex}u, M) = C(u+`\Delta `{=tex}u) - C(u) \]

where `u` is the exact usage term required by the paper, `M` is maximum
capacity, and `Δu` is the legal increment. This generalized expression
should only be used if it matches the verified paper formula and the
code's mapping of `u` is documented. Validate `capacity > 0`,
`increment > 0`, `cost_base > 1`, and
`used_before + increment <= capacity` before calculating. Handle
floating-point precision safely.

### Allocation increments

-   Follow the paper's increment semantics for computation and
    communication resources.
-   Make increment sizes configurable.
-   Round resource quantities only at a documented boundary; avoid
    repeated rounding inside the cost loop.
-   Prevent endless loops due to increments too small to change a float.
-   If the last remaining capacity is smaller than the configured
    increment, either permit a smaller final legal increment or mark the
    resource ineligible. State and test the chosen rule.
-   Log the resource before/after each increment.

### Capacity and admission semantics

-   Admission decision must be atomic.
-   Capacity checks include all active reservations and the proposed
    request.
-   A request that cannot meet its QoS within legal capacity is blocked,
    with a reason code.
-   Distinguish:
    -   `BLOCKED_CAPACITY`
    -   `BLOCKED_QOS_UNSATISFIABLE`
    -   `BLOCKED_NO_ROUTE`
    -   `BLOCKED_INVALID_REQUEST`
    -   `DROPPED_QUEUE_OVERFLOW`
    -   `DROPPED_TIMEOUT` (if the model supports it)
    -   `COMPLETED`
-   Do not label a blocked request as a packet loss unless the metric
    definition explicitly maps admission blocking to a request-loss
    proxy.

------------------------------------------------------------------------

## 8. Edge/cloud placement and topology modes

Implement the topology modes in a staged way; do not pretend they all
exist if only one is implemented.

### Stage A: Edge-only

-   Request goes through access link to edge compute.
-   Useful for demonstrating low propagation delay but constrained edge
    capacity.

### Stage B: Cloud-only

-   Request goes through access link, core/backhaul, then cloud compute.
-   Cloud can have higher capacity but larger propagation/backhaul
    delay.

### Stage C: Parallel/Hybrid edge-cloud

-   Candidate execution placements include edge and cloud.
-   The routing/placement policy must follow the paper's model or a
    clearly documented deterministic adaptation.
-   Cloud fallback can reduce blocking when edge capacity is exhausted,
    but may violate a strict URLLC latency budget.
-   Hybrid must not mean "use both edge and cloud simultaneously" unless
    actual parallel processing is implemented. Otherwise define it as a
    choice between edge and cloud routes/offloading options.

### Topology model configuration

Every mode must define: - Nodes and link endpoints. - Link capacities
and propagation delays. - Compute capacities and base delays. -
Candidate route generation rules. - Allowed resource types and resource
increments. - Whether each request is allowed to offload to cloud. - Any
tenant-specific resource caps, if multi-tenancy is enabled.

### Tenants

The paper includes two tenants, each with eMBB/URLLC/mMTC services. Add
tenant modeling as an extension after the single-tenant core works: -
`tenant_id` must exist in request schemas from the start. - Use at least
two configurable tenants for the paper-aligned scenario. - Tenant-level
SLAs and per-tenant accounting should be separate from slice type. - If
strict tenant isolation is modeled, enforce quotas/partitions. If
resources are shared, clearly state that the implementation is modeling
shared capacity with tenant-level accounting rather than hard
isolation. - A tenant is not the same thing as a slice: each tenant may
have one slice of each service type.

------------------------------------------------------------------------

## 9. Event-driven simulation engine

Use a discrete-event engine rather than incrementing every packet
through the network in a single aggregate formula.

### Event object

Suggested fields: - `time_ms` - `sequence` - `event_type` - `request_id`
/ `packet_id` - `node_id` / `link_id` - `metadata`

Sort events by `(time_ms, sequence)` so simultaneous events resolve
reproducibly.

### Minimum event types

-   `REQUEST_ARRIVAL`
-   `REQUEST_ADMITTED`
-   `REQUEST_BLOCKED`
-   `PACKET_ENQUEUED`
-   `LINK_SERVICE_STARTED`
-   `LINK_SERVICE_COMPLETED`
-   `COMPUTE_SERVICE_STARTED`
-   `COMPUTE_SERVICE_COMPLETED`
-   `PACKET_DELIVERED`
-   `RESOURCE_RELEASED`
-   `QUEUE_OVERFLOW_DROP`
-   `DEADLINE_EXPIRED`

### Event lifecycle

1.  Traffic generator schedules request arrivals.
2.  Arrival event constructs/loads request metadata.
3.  MCRA evaluates a tentative route/resource plan and QoS feasibility.
4.  If accepted, reserve resources atomically and enqueue the
    request/packets on the route.
5.  Each link serializes packets according to its service rate, adds
    propagation delay, and emits completion events.
6.  Compute node processes according to available compute resources and
    emits completion events.
7.  The next hop receives the packet only after the previous hop
    completes.
8.  Destination marks delivery and records end-to-end delay.
9.  Resources are released at the defined completion/cancellation point.
10. Deadline expiry is checked according to a precise policy. Define
    whether expiry means immediate drop or failure-at-completion; don't
    double-count.
11. All transitions append to the event log.
12. At the end of the simulation, report unfinished requests separately
    from blocked and dropped requests.

### Concurrency / capacity semantics

-   Events may overlap in simulated time. The event engine processes
    them in order without advancing wall-clock time.
-   If link service is modeled as a single server, only one packet is
    transmitting at a time on that link; the next starts at the previous
    completion. If the link is modeled as a rate-sharing server, define
    how multiple flows share capacity. Do not combine these models.
-   If compute is modeled as one server, compute service is serialized.
    If multiple parallel workers are modeled, represent their
    count/capacity explicitly.
-   Define whether bandwidth reservations are per-flow guaranteed rates
    or instantaneous aggregate link capacity. Use one interpretation
    consistently.

### State invariants after every event

-   Remaining resource capacity is never negative.
-   Used/reserved capacity never exceeds maximum capacity.
-   A packet cannot be in two nodes/queues simultaneously.
-   A request cannot be both completed and blocked.
-   A resource reservation is released at most once.
-   Event time never moves backwards.
-   A request's parent completes only when its defined completion
    criteria are met.
-   Counters and metrics can be recomputed from the event log for
    validation.

------------------------------------------------------------------------

## 10. Metrics: precise definitions and labels

Do not reuse a metric name if its meaning changes. Keep packet-level and
request-level metrics separate.

### Request-level

-   **Offered requests:** total generated service requests.
-   **Admitted requests:** accepted by MCRA.
-   **Blocked requests:** rejected at admission.
-   **Blocking probability:** `blocked_requests / offered_requests`,
    with a safe zero-denominator rule.
-   **Completed requests:** requests meeting completion criteria.
-   **Completion ratio:** `completed_requests / admitted_requests`.
-   **Deadline success ratio:** completed requests meeting their E2E
    deadline / completed requests or admitted requests; choose
    denominator, label it, and also report the counts.
-   **Mean / median / p95 / p99 E2E delay:** use completed requests
    unless another denominator is explicitly stated.
-   **Mean queueing delay:** average measured queue wait across the
    stated population.
-   **Mean processing delay:** average compute service time.
-   **Mean serialization delay:** average across traversed links or
    packets; label the unit of aggregation.
-   **Timeout rate:** deadline-expired requests / admitted requests, if
    implemented.

### Packet-level

-   Packets generated, transmitted, delivered, dropped.
-   Packet delivery ratio = delivered packets / generated packets.
-   Packet drop ratio = dropped packets / generated packets.
-   Per-hop queue delay, transmission delay, propagation delay.
-   Throughput: successfully delivered payload bits divided by
    simulation observation duration; clearly state whether Mbps is
    decimal.
-   Do not count a single request blocked before packetization as
    multiple packet drops.

### Resource metrics

-   Link utilization time series and average/peak utilization.
-   Compute-node utilization time series and average/peak utilization.
-   Resource utilization must be time-weighted where appropriate, not
    merely average of a few snapshots.
-   Reserved versus actually consumed resource, if these differ.
-   Capacity headroom.
-   Per-slice and per-tenant resource allocation.
-   Resource allocation efficiency: define the exact formula before
    reporting.

### QoS metrics

-   QoS satisfaction: requests meeting all applicable slice QoS
    conditions / the stated denominator.
-   URLLC latency violation count/rate.
-   eMBB throughput target satisfaction, if modeled.
-   mMTC delivery/deadline target satisfaction, if modeled.
-   SLA violation reasons broken down by slice and tenant.
-   Never use a made-up latency formula that directly guarantees a
    favorable result. Compute actual delay from event records.

### MCRA diagnostics

-   Number of MCRA iterations per admitted request.
-   Number of resource increments by type/node.
-   Marginal cost sequence and selected resource at each step.
-   Predicted vs actual E2E delay error.
-   Candidate path/placement attempts.
-   Allocation failure reason.
-   Average decision computation time (optional; distinguish wall-clock
    algorithm runtime from simulated network delay).

------------------------------------------------------------------------

## 11. Dashboard and API integration

Inspect existing Flask routes and front-end code first. Add only the
minimum integration necessary.

### API contract

Add MCRA as a new selectable algorithm or a dedicated endpoint such as
`/api/mcra/simulate`; choose the least disruptive option after
inspection. Do not break `/api/simulate` behavior for existing
algorithms.

Recommended request parameters: - `algorithm: "mcra"` if extending
existing endpoint. -
`topology_mode: "edge_only" | "cloud_only" | "parallel_hybrid"`. -
`scenario`. - `duration_ms`. - `seed`. - `arrival_rate` or per-slice
traffic profile settings. - `access_link_capacity_mbps`. -
`backhaul_capacity_mbps`. - `edge_compute_capacity`. -
`cloud_compute_capacity`. - `queue_capacity_packets`. - `cost_base`. -
`compute_increment`. - `communication_increment`. - Optional tenant
count / tenant configuration.

Validate types, ranges, enum values, and upper bounds. Reject malformed
requests with a structured 400 response; do not crash the Flask app.
Avoid unbounded simulation duration/request counts.

### Response schema

Return JSON with: - `metadata`: seed, scenario, topology, units, model
version, configuration, and assumptions. - `summary`: overall metrics. -
`per_slice`: metrics by eMBB/URLLC/mMTC. - `per_tenant`: if tenants
implemented. - `resource_timeseries`: link and compute utilization by
time. - `requests`: request-level rows. - `packets`: packet-level rows
or a bounded sample plus counts. - `events`: ordered event trace, with a
maximum size / pagination rule. - `mcra_decisions`: allocation loop
traces. - `topology`: nodes, links, routes and their capacities for UI
rendering. - `warnings`: explicit model limitations or unsatisfied
assumptions.

Return only JSON-safe primitives. Handle NaN/infinity and large event
logs safely.

### UI requirements

Create an MCRA area with: 1. **Topology diagram:** nodes, links,
capacities, current utilization; distinguish edge and cloud. 2.
**Simulation controls:** scenario, topology, seed, duration, capacities,
traffic intensity, MCRA cost/increment settings. 3. **Packet journey /
event timeline:** select a request and replay its hops based on actual
timestamps/events. 4. **Live-like simulation replay:** animation may be
accelerated for presentation, but positions and states must be derived
from event data. Provide pause/step/reset only if implemented correctly.
5. **MCRA decision inspector:** show each iteration, eligible resource,
marginal cost, selected increment, predicted delay before/after,
capacity remaining, and reason. 6. **Per-slice metrics:** eMBB, URLLC,
mMTC. 7. **Resource charts:** link and compute utilization over
simulated time. 8. **Latency breakdown:** queue + serialization +
propagation + compute. 9. **Request table:** arrival, route, status,
actual delay, deadline, result reason. 10. **Model assumptions and
caveats:** visible to user, not hidden in code.

The animation must never invent packet travel or latency. If the run is
already complete, render the event timeline/replay from the event log.

------------------------------------------------------------------------

## 12. Experiment design and fair comparisons

Do not mix the old time-step scalar-bandwidth results with the new
event-level MCRA results as if they were generated by the same model.

### Minimum MCRA experiments

Run each scenario over multiple deterministic seeds and report means
plus variation: - Normal mixed traffic. - eMBB surge. - URLLC
emergency. - mMTC surge. - Edge overload. - Backhaul congestion. - Mixed
peak. - Edge-only vs cloud-only vs hybrid, once those modes exist. -
Low, medium, high offered load.

### Fairness

If comparing algorithms in the future: - Generate one request trace per
scenario/seed. - Replay the exact same arrivals, payloads, slice/tenant
IDs, and deadlines for each algorithm. - Give each algorithm an
independent copy of the same initial topology/resource state. - Do not
allow one algorithm to mutate the trace used by another. - Compare
metrics computed from the same definitions. - Explicitly explain if the
existing algorithms cannot be fairly compared because their simulation
models differ.

### Results reporting

-   Save actual run configuration and seed alongside each output.
-   Save request-level and event-level CSV/JSON outputs.
-   Generate plots from real results, not hand-written illustrative
    numbers.
-   Include confidence intervals or standard deviation across seeds
    where useful.
-   Do not assert MCRA "beats" a baseline until experiments support the
    claim.
-   Include at least one failure scenario where MCRA blocks requests
    because QoS is impossible; this demonstrates honest admission
    control.

------------------------------------------------------------------------

## 13. Tests and acceptance criteria

Do not call the feature complete until all of these pass.

### Unit tests

1.  `marginal_cost` returns non-negative finite values for valid inputs
    and increases appropriately with occupancy under the selected cost
    model.
2.  Marginal cost equals the hand-calculated formula for a small known
    example.
3.  Invalid capacity, increment, or cost base is rejected.
4.  A resource increment cannot exceed maximum capacity.
5.  A reservation updates the ledger exactly once.
6.  Release restores capacity exactly once; double release is rejected
    or safely idempotent.
7.  Serialization delay units are correct.
8.  End-to-end delay equals the sum of components in a known
    one-link/one-node route.
9.  Queue order and event tie-breaks are deterministic.
10. Impossible QoS terminates and returns a documented blocked reason.
11. No candidate route returns `BLOCKED_NO_ROUTE`.
12. Queue overflow produces one real drop event.
13. Deadline expiry is not double-counted as both a successful
    completion and a drop.
14. A failed tentative allocation leaves the resource ledger unchanged.
15. Fixed seed yields identical request traces, event order, and
    metrics.
16. Capacity invariants hold after every event.

### Integration tests

1.  MCRA API accepts valid configuration and returns the documented
    schema.
2.  Invalid input returns 400 with an actionable error.
3.  Existing `/api/simulate` legacy calls still work unchanged.
4.  Existing Static, Round-Robin, and QoS-Adaptive outputs are unchanged
    for a fixed seed (golden regression or equivalent tests).
5.  Dashboard can run MCRA and display actual output.
6.  UI request selection filters the actual event trace correctly.
7.  JSON serialization succeeds with no NaN/Infinity.
8.  Large simulations obey configured limits and do not return unbounded
    event payloads.

### Definition of done

-   [ ] Research equations/pseudocode reviewed and mapped to code.
-   [ ] New MCRA engine is isolated from legacy engine.
-   [ ] Topology and resource ledger are explicit.
-   [ ] Request arrivals and event-driven packet travel work.
-   [ ] Edge/cloud routes are implemented to the advertised scope.
-   [ ] MCRA marginal-cost increment loop works and is auditable.
-   [ ] QoS admission/blocking is based on the modeled E2E latency and
    resource constraints.
-   [ ] Actual latency is measured from events.
-   [ ] Dashboard and API work.
-   [ ] Unit/integration/regression tests pass.
-   [ ] Model assumptions and limitations are documented.
-   [ ] Reproducible example configuration and outputs are included.
-   [ ] No fabricated claims, data, or result improvements.

------------------------------------------------------------------------

## 14. Implementation sequence for the coding agent

Implement in small, reviewable stages. After each stage, run tests and
summarize changed files.

### Phase 0 --- Repository reconnaissance

-   Inspect every relevant file: app, templates, CSS/JS, simulator,
    allocator classes, configuration, tests, requirements, README.
-   Run the current app and existing tests.
-   Record current API schema and exact behavior of legacy algorithms.
-   Identify where `app.py` imports/constructs each allocator.
-   Produce a short plan and file mapping before editing.
-   Do not modify files in this phase.

### Phase 1 --- Research mapping

-   Read the complete paper's system model, latency equations,
    resource-allocation workflow, Algorithm 1 and Algorithm 3.
-   Create `docs/MCRA_MODEL.md` with notation-to-code mapping, algorithm
    flow, selected topology subset, all deviations, and citations.
-   Mark each paper feature as `implemented`, `adapted`, `deferred`, or
    `not modeled`.
-   Do not copy the paper's equations from memory.

### Phase 2 --- Data models and units

-   Add request, packet, link, compute node, route, event, allocation
    record, and QoS profile models.
-   Add unit conversion helpers and validation.
-   Add tests before implementing complex behavior.

### Phase 3 --- Resource ledger

-   Implement reserve/release/remaining-capacity operations.
-   Make multi-resource reservation atomic.
-   Add invariants and tests for no overbooking/double release.

### Phase 4 --- Topology and latency

-   Build edge-only topology first, with real link and compute service
    models.
-   Implement route traversal and component latency accounting.
-   Test one-link, two-link, edge, and cloud path calculations.

### Phase 5 --- Traffic + discrete-event engine

-   Generate deterministic arrivals.
-   Implement event queue, link queues, compute queues, packet
    transitions, deadlines, completion, release.
-   Ensure packet states and event timestamps are consistent.

### Phase 6 --- MCRA marginal-cost engine

-   Implement the verified marginal cost function as a pure unit-tested
    function.
-   Implement tentative increment selection and predicted latency
    recomputation.
-   Add trace records for every candidate and chosen increment.
-   Enforce termination and capacity limits.
-   Verify edge-only MCRA before adding cloud/hybrid candidate
    selection.

### Phase 7 --- Admission and resource lifecycle

-   Integrate initial allocation, latency feasibility, incremental
    allocation, final resource check, atomic commit, blocking, and
    release.
-   Test every rejection reason and rollback path.
-   Make sure MCRA does not simply allocate the whole capacity to one
    request.

### Phase 8 --- Topology expansion and tenants

-   Add cloud-only and parallel/hybrid options according to the verified
    paper model.
-   Add two tenants and per-tenant slice accounting.
-   Keep the distinction between tenant and slice explicit.
-   If any feature is too large, finish and document a correct subset
    rather than adding nonfunctional UI toggles.

### Phase 9 --- Metrics and result export

-   Implement the precise metrics in Section 10.
-   Recompute selected metrics from event logs as a validation check.
-   Export request, packet, event, resource timeseries, and MCRA
    decision logs.

### Phase 10 --- Flask/UI integration

-   Add MCRA without changing legacy behavior.
-   Validate API input and output.
-   Add topology, metrics, request inspector, decision trace, and
    timeline/replay.
-   Render a useful error state for invalid settings or failed
    simulations.

### Phase 11 --- Experiments and documentation

-   Run repeatable scenarios and multiple seeds.
-   Export raw outputs and plots generated from actual runs.
-   Explain observed behavior; do not write conclusions before seeing
    data.
-   Update README with run instructions, model scope, assumptions,
    tests, and limitations.

### Phase 12 --- Final audit

-   Run all old and new tests.
-   Compare legacy fixed-seed outputs before and after.
-   Search for unbounded loops, unhandled NaNs, unit mismatches, stale
    UI fields, and misleading metric labels.
-   Confirm all UI values come from backend simulation output.
-   Provide a concise final report listing implemented features, exact
    files changed, test results, known limitations, and commands to run.

------------------------------------------------------------------------

## 15. Coding standards

-   Follow the repository's current Python version and style.
-   Use type hints for public interfaces and dataclasses/enums where
    helpful.
-   Keep algorithm code independent of Flask and visualization.
-   Use a seeded RNG object passed into traffic generation; avoid global
    random state.
-   Keep functions small and testable.
-   Use structured reason codes instead of parsing human-readable
    strings.
-   Use logging or structured event records, not only `print`.
-   Avoid excessive dependencies. If adding a dependency, explain why
    and update requirements.
-   Never catch and silently discard broad exceptions.
-   Validate all external inputs.
-   Add comments that explain network-model assumptions and algorithmic
    reasoning, not obvious syntax.
-   Avoid claiming "real-world accurate" when the system is a simplified
    simulation. Say "research-grounded educational model with explicit
    assumptions."

------------------------------------------------------------------------

## 16. Final agent response format

When finished, report: 1. Summary of what was implemented. 2. Exact list
of files added/modified. 3. How the MCRA cost equation maps to code and
the source section used. 4. What network topology and packet lifecycle
are actually simulated. 5. Which features are paper-faithful, adapted,
or deferred. 6. Test commands and actual pass/fail results. 7. How to
launch the dashboard and run an MCRA simulation. 8. Where CSV/JSON/plots
are saved. 9. Known limitations and recommended next step.

Do not say "done" if any acceptance criterion is unimplemented. Separate
implemented features from future work.

------------------------------------------------------------------------

## 17. References

1.  Lin, J.-Y., Chou, P.-H., & Hwang, R.-H. (2023). *Dynamic Resource
    Allocation for Network Slicing with Multi-Tenants in 5G Two-Tier
    Networks*. Sensors, 23(10), 4698. https://doi.org/10.3390/s23104698\
    Full text: https://www.mdpi.com/1424-8220/23/10/4698\
    This is the primary source for the MCRA algorithm, two-tier model,
    resource cost, latency constraints, and admission/blocking workflow.

2.  The existing project repository:
    https://github.com/VivekMishra5210/5G-Network-Slicing-Simulator\
    The coding agent must inspect the live repository state before
    choosing concrete filenames or modifying integration points.

### Final reminder

**Build the simulator around the network model and the algorithm, not
around a dashboard animation.** Packets, queues, latency, capacity,
allocation decisions, and metrics must be linked through actual
simulation state and event records. Keep MCRA additive and isolated so
the project's existing algorithms remain intact.
