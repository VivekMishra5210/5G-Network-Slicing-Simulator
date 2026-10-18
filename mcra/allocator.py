"""
MCRA (Minimum Cost Resource Allocation) Iterative Decision Loop.

Implements the research paper's core iterative marginal-cost resource allocation,
capacity limits, latency constraints, and admission/blocking rules.

Reference:
Jia-You Lin et al., Sensors 23(10), 4698 (2023).
"""

from typing import List, Dict, Tuple, Optional, Any
from mcra.models import (
    ServiceRequest,
    Route,
    ResourceType,
    RequestStatus,
    AllocationStepTrace,
    MCRADecisionTrace,
)
from mcra.resources import ResourceLedger
from mcra.latency import predict_route_e2e_delay_ms
from allocators.mcra_allocator import marginal_cost


class MCRAAllocator:
    """
    Evaluates candidate routes and iteratively refines resource allocations using
    the lowest marginal cost criterion until deadline is met or resources are exhausted.
    """

    def __init__(
        self,
        cost_base: float = 2.0,
        comm_increment_mbps: float = 1.0,
        compute_increment_units: float = 0.5,
        max_iterations: int = 50,
    ):
        self.cost_base = cost_base
        self.comm_increment_mbps = comm_increment_mbps
        self.compute_increment_units = compute_increment_units
        self.max_iterations = max_iterations

    def admit_request(
        self,
        request: ServiceRequest,
        candidate_routes: List[Route],
        ledger: ResourceLedger,
        current_time_ms: float = 0.0,
    ) -> Tuple[bool, Optional[Route], Dict[str, float], float, MCRADecisionTrace, RequestStatus]:
        """
        Attempt to allocate resources for a request across candidate routes using MCRA.
        Returns:
            (admitted, selected_route, allocated_plan, predicted_delay, decision_trace, status)
        """
        if not candidate_routes:
            trace = MCRADecisionTrace(
                request_id=request.request_id,
                tenant_id=request.tenant_id,
                slice_type=request.slice_type.value,
                route_name="none",
                deadline_ms=request.deadline_ms,
                admitted=False,
                status_reason="No candidate route available",
                final_predicted_delay_ms=float("inf"),
            )
            return False, None, {}, float("inf"), trace, RequestStatus.BLOCKED_NO_ROUTE

        last_trace: Optional[MCRADecisionTrace] = None
        last_status = RequestStatus.BLOCKED_CAPACITY

        for route in candidate_routes:
            admitted, plan, pred_delay, trace, status = self._evaluate_route(
                request=request,
                route=route,
                ledger=ledger,
                current_time_ms=current_time_ms,
            )
            last_trace = trace
            last_status = status

            if admitted:
                # Successfully admitted on this route!
                return True, route, plan, pred_delay, trace, RequestStatus.ADMITTED

        # All candidate routes failed
        return False, None, {}, last_trace.final_predicted_delay_ms if last_trace else 0.0, last_trace, last_status

    def _evaluate_route(
        self,
        request: ServiceRequest,
        route: Route,
        ledger: ResourceLedger,
        current_time_ms: float,
    ) -> Tuple[bool, Dict[str, float], float, MCRADecisionTrace, RequestStatus]:
        """Evaluate and optimize resource allocation on a specific candidate route."""
        decision_trace = MCRADecisionTrace(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            slice_type=request.slice_type.value,
            route_name=route.path_name,
            deadline_ms=request.deadline_ms,
            admitted=False,
            status_reason="",
            final_predicted_delay_ms=0.0,
        )

        # Step 1: Initial minimum allocation trial
        # Assign base units: e.g. 2.0 Mbps per link, 1.0 unit per compute node
        tentative_plan: Dict[str, float] = {}
        for link in route.links:
            tentative_plan[link.link_id] = 2.0
        tentative_plan[route.compute_node.node_id] = 1.0

        decision_trace.initial_allocations = dict(tentative_plan)

        # Check if initial allocations exceed remaining ledger capacity
        if not ledger.check_availability(tentative_plan):
            decision_trace.status_reason = "Insufficient capacity for initial minimum allocation"
            decision_trace.final_predicted_delay_ms = float("inf")
            return False, {}, float("inf"), decision_trace, RequestStatus.BLOCKED_CAPACITY

        pred_delay = predict_route_e2e_delay_ms(
            payload_bits=request.payload_bits,
            compute_demand=request.compute_demand,
            route=route,
            allocations=tentative_plan,
        )

        iteration = 0

        # Step 2: Refinement loop if delay exceeds deadline
        while pred_delay > request.deadline_ms and iteration < self.max_iterations:
            iteration += 1

            # Find eligible resources on path with remaining capacity in ledger
            candidates_eval = []
            best_resource: Optional[str] = None
            best_res_type: Optional[str] = None
            best_cost = float("inf")
            best_inc = 0.0
            best_new_delay = pred_delay

            # 1. Check Links
            for link in route.links:
                res_id = link.link_id
                inc = self.comm_increment_mbps
                current_plan_val = tentative_plan[res_id]
                max_cap = link.capacity_mbps
                cur_used = ledger.get_used(res_id)

                # Check if ledger can accommodate (tentative + inc)
                if current_plan_val + inc <= max_cap and (cur_used + current_plan_val + inc) <= max_cap:
                    cost = marginal_cost(
                        used_before=cur_used + current_plan_val,
                        increment=inc,
                        capacity=max_cap,
                        cost_base=self.cost_base,
                    )
                    test_plan = dict(tentative_plan)
                    test_plan[res_id] += inc
                    test_delay = predict_route_e2e_delay_ms(
                        request.payload_bits, request.compute_demand, route, test_plan
                    )
                    candidates_eval.append({
                        "resource_id": res_id,
                        "type": "communication",
                        "marginal_cost": round(cost, 6),
                        "resulting_delay": round(test_delay, 3),
                    })

                    if cost < best_cost:
                        best_cost = cost
                        best_resource = res_id
                        best_res_type = "communication"
                        best_inc = inc
                        best_new_delay = test_delay

            # 2. Check Compute Node
            c_node = route.compute_node
            c_id = c_node.node_id
            c_inc = self.compute_increment_units
            c_plan_val = tentative_plan[c_id]
            c_cap = c_node.capacity_units
            c_used = ledger.get_used(c_id)

            if c_plan_val + c_inc <= c_cap and (c_used + c_plan_val + c_inc) <= c_cap:
                cost = marginal_cost(
                    used_before=c_used + c_plan_val,
                    increment=c_inc,
                    capacity=c_cap,
                    cost_base=self.cost_base,
                )
                test_plan = dict(tentative_plan)
                test_plan[c_id] += c_inc
                test_delay = predict_route_e2e_delay_ms(
                    request.payload_bits, request.compute_demand, route, test_plan
                )
                candidates_eval.append({
                    "resource_id": c_id,
                    "type": "computation",
                    "marginal_cost": round(cost, 6),
                    "resulting_delay": round(test_delay, 3),
                })

                # Prefer compute if costs are equal
                if cost < best_cost:
                    best_cost = cost
                    best_resource = c_id
                    best_res_type = "computation"
                    best_inc = c_inc
                    best_new_delay = test_delay

            # If no legal increment can be applied, capacity is exhausted
            if best_resource is None:
                decision_trace.status_reason = "Capacity exhausted on all path resources before QoS could be met"
                decision_trace.final_predicted_delay_ms = pred_delay
                return False, {}, pred_delay, decision_trace, RequestStatus.BLOCKED_CAPACITY

            # Apply lowest-cost increment to tentative plan
            old_delay = pred_delay
            tentative_plan[best_resource] += best_inc
            pred_delay = best_new_delay

            step_trace = AllocationStepTrace(
                iteration=iteration,
                selected_resource=best_resource,
                resource_type=best_res_type,
                increment=best_inc,
                marginal_cost=best_cost,
                candidates_evaluated=candidates_eval,
                predicted_delay_before=old_delay,
                predicted_delay_after=pred_delay,
                remaining_capacity_after=ledger.get_remaining(best_resource) - tentative_plan[best_resource],
            )
            decision_trace.iterations.append(step_trace)

        # Step 3: Feasibility and Admission Termination
        decision_trace.final_allocations = dict(tentative_plan)
        decision_trace.final_predicted_delay_ms = pred_delay

        if pred_delay > request.deadline_ms:
            if iteration >= self.max_iterations:
                decision_trace.status_reason = f"Search limit reached ({self.max_iterations} iterations) without satisfying deadline"
                return False, {}, pred_delay, decision_trace, RequestStatus.BLOCKED_SEARCH_LIMIT
            else:
                decision_trace.status_reason = "QoS deadline unsatisfiable with available path capacity"
                return False, {}, pred_delay, decision_trace, RequestStatus.BLOCKED_QOS_UNSATISFIABLE

        # Final capacity verification and atomic reservation commit
        reservation_id = f"res_{request.request_id}"
        committed = ledger.reserve_atomic(
            reservation_id=reservation_id,
            allocations=tentative_plan,
            current_time_ms=current_time_ms,
        )

        if not committed:
            decision_trace.status_reason = "Atomic resource reservation conflict"
            return False, {}, pred_delay, decision_trace, RequestStatus.BLOCKED_CAPACITY

        decision_trace.admitted = True
        decision_trace.status_reason = "Admitted successfully meeting QoS deadline"
        request.reservation_id = reservation_id
        request.allocated_resources = dict(tentative_plan)
        request.predicted_delay_ms = pred_delay

        return True, tentative_plan, pred_delay, decision_trace, RequestStatus.ADMITTED
