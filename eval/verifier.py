"""
Deterministic verifier (Section 8.9's dependent variable, Section 9's
taxonomy in miniature). Diffs a run's Trajectory against its gold
trajectory. No LLM judge anywhere in this file -- every check is a plain
comparison, which is the whole point of the no-human-annotation constraint
(Section 3.6).
"""

from agent.react_loop import Trajectory


def verify(traj: Trajectory, gold: dict) -> dict:
    """
    Returns a dict of scored fields, one record's worth of the run log
    described in Appendix E. Only implements the checks this scaffold's
    one example task needs; extend per Section 9's full taxonomy in
    Phase 2.
    """
    gold_steps = gold["gold_steps"]
    gold_terminal = gold["terminal_state"]

    # -- success: terminal state matches gold exactly ------------------
    success = traj.terminal_state == gold_terminal

    # -- constraint survival: did the booked flight actually satisfy
    #    every constraint in the task, not just match gold by luck? -----
    constraints = gold["constraints"]
    constraints_survived = None
    booked = next(
        (s["result"] for s in traj.steps if s.get("tool") == "book_flight" and "result" in s),
        None,
    )
    if booked is not None:
        # Re-derive the booked flight's own record to check its fields,
        # since terminal_state only carries flight_id/price.
        from env.data.flights import FLIGHTS
        flight = next((f for f in FLIGHTS if f["flight_id"] == booked["booking.flight_id"]), None)
        if flight is not None:
            constraints_survived = (
                flight["depart_time"] < constraints["depart_before"]
                and flight["price"] <= constraints["max_price"]
            )

    # -- fact displacement: was a value the agent itself retrieved
    #    earlier (e.g. from get_seat_availability) restated differently
    #    later (e.g. in the booking args)? -------------------------------
    fact_displacements = 0
    seen_flight_ids = set()
    for s in traj.steps:
        if s.get("tool") == "get_seat_availability" and "result" in s:
            seen_flight_ids.add(s["result"]["flight_id"])
        if s.get("tool") == "book_flight" and "args" in s:
            booked_id = s["args"].get("flight_id")
            if seen_flight_ids and booked_id not in seen_flight_ids:
                fact_displacements += 1

    # -- final grounding: does every value in the terminal state trace
    #    back to some tool output the agent actually received? ----------
    all_tool_values = set()
    for s in traj.steps:
        if "result" in s:
            all_tool_values.update(str(v) for v in s["result"].values())
    final_grounding_ok = all(
        str(v) in all_tool_values for v in traj.terminal_state.values()
    ) if traj.terminal_state else False

    return {
        "success": success,
        "first_error_step": traj.first_error_step,
        "constraints_survived": constraints_survived,
        "fact_displacements": fact_displacements,
        "final_grounding_ok": final_grounding_ok,
        "num_steps_taken": len(traj.steps),
        "num_steps_gold": len(gold_steps),
        "injected_error": traj.injected_error,
        "recovered": traj.recovered_after_injection,
    }
