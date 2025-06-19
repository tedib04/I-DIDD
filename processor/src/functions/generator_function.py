from itertools import permutations
from math import ceil
from typing import List, Tuple, Set

from pyflink.common import Types
from pyflink.datastream import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import (
    MapStateDescriptor, ValueStateDescriptor,
    MapState, ValueState, ListState, ListStateDescriptor
)

from processor.src.automata.constraint_automaton import ConstraintAutomaton
from processor.src.utils.types import Constraint, ConstraintEventPair


class FrequentCandidateConstraintGenerator(KeyedProcessFunction):

    def __init__(self, apriori_min_support: float):
        self.local_automaton = None
        self.event_idx = None
        self.history = None
        self.all_constraints = None
        self.joint_counts = None
        self.trace_pair_seen = None
        self.activity_trace_counts = None
        self.trace_seen = None
        self.activities_in_trace = None
        self.apriori_min_support = apriori_min_support

    def open(self, ctx: RuntimeContext) -> None:
        # 1) Track distinct traces seen
        self.trace_seen: ListState[str] = ctx.get_list_state(ListStateDescriptor("trace_seen", Types.STRING()))

        # 2) Singleton support: count per activity in distinct traces
        self.activity_trace_counts: MapState[str, int] = ctx.get_map_state(
            MapStateDescriptor("activity_trace_counts", Types.STRING(), Types.INT())
        )

        # 3) Track which concept_names seen per trace for joint support
        self.activities_in_trace: MapState[str, Set[str]] = ctx.get_map_state(
            MapStateDescriptor("activities_in_trace", Types.STRING(), Types.PICKLED_BYTE_ARRAY())
        )

        # 4) Track which pairs counted per trace to avoid double-counting
        self.trace_pair_seen: MapState[str, Set[Tuple[str, str]]] = ctx.get_map_state(
            MapStateDescriptor("trace_pair_seen", Types.STRING(), Types.PICKLED_BYTE_ARRAY())
        )

        # 5) Joint support counts for candidate pairs
        self.joint_counts: MapState[Tuple[str, str], int] = ctx.get_map_state(
            MapStateDescriptor("joint_counts", Types.PICKLED_BYTE_ARRAY(), Types.INT())
        )

        # 6) Accumulate active candidate constraints
        self.all_constraints: ValueState[List[Constraint]] = ctx.get_state(
            ValueStateDescriptor("all_constraints", Types.PICKLED_BYTE_ARRAY()))

        # 7) Persist history of activity_name strings per trace
        self.history: MapState[str, List[str]] = ctx.get_map_state(
            MapStateDescriptor("trace_history", Types.STRING(), Types.PICKLED_BYTE_ARRAY())
        )

        # 8) For naming each event uniquely
        self.event_idx: ValueState[int] = ctx.get_state(ValueStateDescriptor("event_idx", Types.INT()))

        # 9) Automaton state per constraint template
        self.local_automaton: ValueState = ctx.get_state(
            ValueStateDescriptor("local_automaton", Types.PICKLED_BYTE_ARRAY()))

    def process_element(self, pair: ConstraintEventPair, ctx: KeyedProcessFunction.Context):
        trace_id: str = pair['event']['case_concept_name']
        activity: str = pair['event']['concept_name']
        constraint_name: str = pair['constraint']

        # Step 1: Update the total number of traces
        if trace_id not in self.trace_seen.get():
            self.trace_seen.add(trace_id)

        # Step 2: Update set of activities seen in this trace
        trace_activities: Set[str] = self.activities_in_trace.get(trace_id) or set()
        new_activity_in_trace: bool = activity not in trace_activities
        if new_activity_in_trace:
            trace_activities.add(activity)
            self.activities_in_trace.put(trace_id, trace_activities)
            activity_count: int = (self.activity_trace_counts.get(activity) or 0) + 1
            self.activity_trace_counts.put(activity, activity_count)

        # Step 3: Calculate the minimum support threshold based on current trace count
        threshold: float = ceil(self.apriori_min_support * len(list(self.trace_seen)))

        # Step 5: If this is a new frequent activity, generate candidate pairs with other frequent activities
        current_list = self.all_constraints.value() or []
        seen_keys = {(c.first_activity, c.second_activity) for c in current_list}
        new_pairs: List[Constraint] = []
        if new_activity_in_trace and self.activity_trace_counts.get(activity) >= threshold:
            for other, other_count in self.activity_trace_counts.items():
                if other == activity or other_count < threshold:
                    continue
                for first, second in permutations([activity, other], 2):
                    key = (first, second)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        new_pairs.append(Constraint(
                            name=constraint_name,
                            first_activity=first,
                            second_activity=second
                        ))

        # Update state with any new candidate constraints
        current_list.extend(new_pairs)
        self.all_constraints.update(current_list)

        # Step 6: Count joint support for candidate pairs within this trace
        pair_seen: Set[Tuple[str, str]] = self.trace_pair_seen.get(trace_id) or set()
        for c in current_list:
            key = (c.first_activity, c.second_activity)
            # if both activities seen in this trace and not yet counted
            if c.first_activity in trace_activities and c.second_activity in trace_activities and key not in pair_seen:
                pair_seen.add(key)
                count: int = (self.joint_counts.get(key) or 0) + 1
                self.joint_counts.put(key, count)
        self.trace_pair_seen.put(trace_id, pair_seen)

        # Step 7: Prune constraints that don't meet the joint support threshold
        pruned: List[Constraint] = []
        for c in current_list:
            key = (c.first_activity, c.second_activity)
            if (self.joint_counts.get(key) or 0) >= threshold:
                pruned.append(c)
        self.all_constraints.update(pruned)

        # Step 8: Create a unique name for this activity based on the index
        idx: int = (self.event_idx.value() or 0) + 1
        self.event_idx.update(idx)
        activity_name = f"{activity}_{idx}"

        # Step 9: Initialize the constraint automaton if not already done
        if not self.local_automaton.value():
            self.local_automaton.update(ConstraintAutomaton.create(constraint_name))

        # Step 10: Append this activity to the trace's history
        self.history.put(trace_id, (self.history.get(trace_id) or []) + [activity_name])

        for c in pruned:
            yield {
                'constraint': c,
                'activity_name': activity_name,
                'automaton': self.local_automaton.value(),
                'event': pair['event'],
                'before_in_trace': self.history.get(trace_id)
            }
