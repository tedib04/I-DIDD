from abc import ABC
from typing import Dict, List, Set

from pm4py.objects.log.obj import Event
from pyflink.datastream.state import MapState

from processor.src.automata.constraint_automaton import ConstraintAutomaton, AutomatonColor
from processor.src.utils.types import Constraint, Token


@ConstraintAutomaton.register('Alternate Response')
class AlternateResponseConstraintAutomaton(ConstraintAutomaton, ABC):
    """
    Implements a Deterministic Finite Automaton (DFA) for the 'Alternate Response' constraint
    in the DECLARE process modeling language. This constraint requires that whenever
    the activation event (a) occurs, the target event (b) must occur afterward, before A recurs.
    The implementation uses future information (triggered only at activation)
    to track the constraint activation state (fulfilled or violated).

    For a visual representation of the DFA corresponding to this constraint, please refer to the diagram located at:
    `assets/dfa/images/alternate_response.png`
    """

    def __init__(self, constraint_name: str):
        super().__init__(constraint_name=constraint_name,
                         formula='G((a) -> X[!]((!(a)U(b))))',
                         activation='a',
                         target='b')
        self.permanently_violated_state: int = 2

    def process_event(self,
                      constraint: Constraint,
                      event: Event,
                      activity: str,
                      trace_id: str,
                      active_constraints: MapState,
                      fulfillment_ratio_utils: MapState,
                      **kwargs) -> Dict:

        if self.is_activation(activity=activity, constraint_activation=constraint.first_activity):
            self.generate_token_in_automaton(
                token=Token(constraint=constraint, activation=activity, trace_id=trace_id),
                active_constraints=active_constraints,
                payload=event,
                fulfillment_ratio_utils=fulfillment_ratio_utils)

        activations: Dict = {'fulfilling': [], 'violating': []}
        to_remove: List[Constraint] = []

        for token, state in active_constraints.items():
            if token.trace_id == trace_id:

                self.move_automaton(
                    activity=self.map_activity_to_placeholder(activity, token.constraint),
                    constraint_state=state,
                    trace_id=trace_id
                )

                if state['color'] == AutomatonColor.TEMPORARILY_SATISFIED:
                    state['color'] = AutomatonColor.PERMANENTLY_SATISFIED
                    activations['fulfilling'].append((token, state))
                    to_remove.append(token)
                    self.update_fulfillment_ratio(fulfillment_ratio_utils, token)
                elif state['color'] == AutomatonColor.PERMANENTLY_VIOLATED:
                    activations['violating'].append((token, state))
                    to_remove.append(token)

        for token in to_remove:
            active_constraints.remove(token)

        if event['is_end_event']:
            violating_activations = self.cleanup_violations_at_trace_end(active_constraints, trace_id)
            activations['violating'].extend(violating_activations)

        return activations

    def update_constraint_state(self, constraint_state: Dict, next_state: Set, trace_id: str) -> None:
        constraint_state['current_state'] = next_state
        current: int = list(constraint_state['current_state'])[0]

        # State nr.2
        if current == self.permanently_violated_state:
            constraint_state['color'] = AutomatonColor.PERMANENTLY_VIOLATED
        # State nr.0
        elif self.dfa.is_accepting(current):
            constraint_state['color'] = AutomatonColor.TEMPORARILY_SATISFIED
        # State nr.1
        else:
            constraint_state['color'] = AutomatonColor.TEMPORARILY_VIOLATED
