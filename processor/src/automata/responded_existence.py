from abc import ABC
from typing import Dict, List, Set

from pm4py.objects.log.obj import Event
from pyflink.datastream.state import MapState

from processor.src.automata.constraint_automaton import ConstraintAutomaton, AutomatonColor
from processor.src.utils.types import Constraint, Token


@ConstraintAutomaton.register('Responded Existence')
class RespondedExistenceConstraintAutomaton(ConstraintAutomaton, ABC):
    """
    Implements a Deterministic Finite Automaton (DFA) for the 'Responded Existence' constraint
    in the DECLARE process modeling language. This constraint requires that whenever
    the activation event (a) occurs, the target event (b) must occur as well (either before or after the activation event).
    The implementation uses past (trace level) as well as future information (triggered only at activation)
    to track the constraint activation state (fulfilled or violated).

    For a visual representation of the DFA corresponding to this constraint, please refer to the diagram located at:
    `assets/dfa/images/responded_existence.png`
    """

    def __init__(self, constraint_name: str):
        super().__init__(constraint_name=constraint_name,
                         formula='(F(a) -> (F(b)))',
                         activation='a',
                         target='b')
        self.permanently_satisfied_state: int = 1

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

        flag: bool = constraint.second_activity in seen_target[:-1]

        if self.is_activation(activity=activity, constraint_activation=constraint.first_activity):
            # (1) If we have seen the target before in the trace, then the activation is classified as fulfillment,
            # and we move the automaton to the permanently satisfied state.
            if flag:
                token: Token = Token(constraint=constraint, activation=activity, trace_id=trace_id)
                state = {'color': AutomatonColor.PERMANENTLY_SATISFIED, 'current_state': 1, 'payload': event}
                activations['fulfilling'].append((token, state))
                self.update_activation_count(fulfillment_ratio_utils, token)
                self.update_fulfillment_ratio(fulfillment_ratio_utils, token)
            else:
                # (2)  If we have NOT seen the target before in the trace, then we create a new automaton to keep track if the activation will
                # become a fulfillment in the future
                self.generate_token_in_automaton(token=Token(constraint=constraint, activation=activity, trace_id=trace_id),
                                                 active_constraints=active_constraints,
                                                 payload=event,
                                                 fulfillment_ratio_utils=fulfillment_ratio_utils)

        # Update all active automata of the current trace, using as input symbol the current event.
        for token, state in active_constraints.items():
            if token.trace_id == trace_id:
                self.move_automaton(activity=self.map_activity_to_placeholder(activity, token.constraint),
                                    constraint_state=state,
                                    trace_id=trace_id)

                # Check for terminal states
                if state['color'] == AutomatonColor.PERMANENTLY_SATISFIED:
                    activations['fulfilling'].append((token, state))
                    to_remove.append(token)
                    self.update_fulfillment_ratio(fulfillment_ratio_utils, token)

        # Remove activations that have been fulfilled from before.
        for token in to_remove:
            active_constraints.remove(token)

        # If the current event marks the end of the trace, update all activations currently marked as temporarily violated to permanently violated.
        if event['is_end_event']:
            violating = self.cleanup_violations_at_trace_end(active_constraints, trace_id)
            activations['violating'].extend(violating)

        return activations

    def update_constraint_state(self, constraint_state: Dict, next_state: Set, trace_id: str) -> None:
        constraint_state['current_state'] = next_state
        current: int = list(constraint_state['current_state'])[0]

        if current == self.permanently_satisfied_state:
            constraint_state['color'] = AutomatonColor.PERMANENTLY_SATISFIED
        elif current == 2:
            constraint_state['color'] = AutomatonColor.TEMPORARILY_VIOLATED
        else:
            constraint_state['color'] = AutomatonColor.TEMPORARILY_SATISFIED
