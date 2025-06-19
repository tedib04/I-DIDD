from abc import ABC
from typing import Dict, List, Set

from pm4py.objects.log.obj import Event
from pyflink.datastream.state import MapState

from processor.src.automata.constraint_automaton import ConstraintAutomaton, AutomatonColor
from processor.src.utils.types import Constraint, Token


@ConstraintAutomaton.register('Precedence')
class PrecedenceConstraintAutomaton(ConstraintAutomaton, ABC):
    """
    Implements a Deterministic Finite Automaton (DFA) for the 'Precedence' constraint
    in the DECLARE process modeling language. This constraint requires that whenever
    the activation event (b) occurs, the target event (a) must have been executed before (b).
    The implementation uses past information (triggered only at activation)
    to track the constraint activation state (fulfilled or violated).

    For a visual representation of the DFA corresponding to this constraint, please refer to the diagram located at:
    `assets/dfa/images/precedence.png`
    """

    def __init__(self, constraint_name: str):
        super().__init__(constraint_name=constraint_name,
                         formula='((!(b)) U (a)) || G(!(b))',
                         activation='b',
                         target='a')
        self.permanently_satisfied_state: int = 2

    def process_event(self,
                      constraint: Constraint,
                      event: Event,
                      activity: str,
                      trace_id: str,
                      active_constraints: MapState,
                      fulfillment_ratio_utils: MapState,
                      seen_target: List[str]) -> Dict:

        activations: Dict = {'fulfilling': [], 'violating': []}
        to_remove: List = []

        if self.is_activation(activity=activity, constraint_activation=constraint.second_activity):
            self.generate_token_in_automaton(token=Token(constraint=constraint, activation=activity, trace_id=trace_id),
                                             active_constraints=active_constraints,
                                             payload=event,
                                             fulfillment_ratio_utils=fulfillment_ratio_utils)

        for token, state in active_constraints.items():
            if token.trace_id == trace_id:
                for element in self.get_prefix(seen_target, constraint.first_activity):
                    self.move_automaton(
                        activity=self.map_activity_to_placeholder(element, token.constraint),
                        constraint_state=state,
                        trace_id=trace_id
                    )

                    if state['color'] == AutomatonColor.PERMANENTLY_SATISFIED:
                        activations['fulfilling'].append((token, state))
                        to_remove.append(token)
                        self.update_fulfillment_ratio(fulfillment_ratio_utils, token)
                        break
                    elif state['color'] == AutomatonColor.PERMANENTLY_VIOLATED:
                        activations['violating'].append((token, state))
                        to_remove.append(token)
                        break

                if state['color'] == AutomatonColor.TEMPORARILY_SATISFIED:
                    state['color'] = AutomatonColor.PERMANENTLY_SATISFIED
                    activations['fulfilling'].append((token, state))
                    to_remove.append(token)
                    self.update_fulfillment_ratio(fulfillment_ratio_utils, token)

        for token in to_remove:
            active_constraints.remove(token)

        return activations

    def update_constraint_state(self, constraint_state: Dict, next_state: Set, trace_id: str) -> None:
        constraint_state['current_state'] = next_state
        current: int = list(constraint_state['current_state'])[0]

        if current == self.permanently_satisfied_state:
            constraint_state['color'] = AutomatonColor.PERMANENTLY_SATISFIED
        elif current == 1:
            constraint_state['color'] = AutomatonColor.PERMANENTLY_VIOLATED
        # No need to add color to state 0 as we are considering only non-vacuous satisfaction. As a consequence no token can ever stay in position 0
