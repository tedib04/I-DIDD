import copy
from abc import ABC, ABCMeta
from abc import abstractmethod
from enum import Enum, unique
from functools import reduce
from typing import Set, Dict, List, Tuple

from logaut import ltl2dfa
from pm4py.objects.log.obj import Event
from pyflink.datastream.state import MapState
from pylogics.parsers import parse_ltl
from pythomata.core import DFA

from processor.src.utils.types import Constraint, Token


@unique
class AutomatonColor(Enum):
    PERMANENTLY_SATISFIED = "Permanently Satisfied"
    PERMANENTLY_VIOLATED = "Permanently Violated"
    TEMPORARILY_VIOLATED = "Temporarily Violated"
    TEMPORARILY_SATISFIED = "Temporarily Satisfied"


class ConstraintAutomaton(ABC):
    """Abstract class to represent and provide support for dealing with DFA."""

    _registry: dict[str, type["ConstraintAutomaton"]] = {}

    def __init__(self, **kwargs) -> None:
        self.constraint_name: str = kwargs['constraint_name']
        self.ltl_formula: str = kwargs['formula']
        self.activation: str = kwargs['activation']
        self.target: str = kwargs['target']
        self.dfa: DFA = self.create_automaton()
        self.initial_state: Set = {self.dfa.initial_state}

    @classmethod
    def register(cls, template_name: str):
        def decorator(subclass: type[ConstraintAutomaton]):
            cls._registry[template_name] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, template_name: str, *args, **kwargs) -> "ConstraintAutomaton":
        try:
            automaton_cls: ABCMeta = cls._registry[template_name]
        except KeyError:
            raise ValueError(f"No automaton registered for template '{template_name}'")
        return automaton_cls(template_name, *args, **kwargs)

    @abstractmethod
    def process_event(self, **kwargs) -> None:
        pass

    @abstractmethod
    def update_constraint_state(self, constraint_state: Dict, next_state: Set, trace_id: str) -> None:
        pass

    def create_automaton(self) -> DFA:
        automaton: DFA = ltl2dfa(parse_ltl(self.ltl_formula), backend="lydia")
        return automaton

    @staticmethod
    def get_current_state(constraint) -> Set:
        return constraint["current_state"]

    @staticmethod
    def is_activation(activity: str, constraint_activation: str) -> bool:
        return activity.split("_")[0] == constraint_activation

    @staticmethod
    def is_target(current_activity: str, constraint_target: str) -> bool:
        return current_activity.split("_")[0] == constraint_target

    def generate_token_in_automaton(self,
                                    token: Token,
                                    active_constraints,
                                    payload: Event,
                                    fulfillment_ratio_utils: MapState) -> None:
        active_constraints.put(key=token,
                               value={"color": None, "current_state": self.initial_state, "payload": payload})
        self.update_activation_count(fulfillment_ratio_utils, token)

    @staticmethod
    def update_activation_count(fulfillment_ratio_utils, triple: Token) -> None:
        metrics = fulfillment_ratio_utils.get(key=triple.constraint)
        if metrics:
            fulfillment_ratio_utils.put(key=triple.constraint,
                                        value={'activation_count': metrics['activation_count'] + 1,
                                               'fulfillment_count': metrics['fulfillment_count']})
        else:
            fulfillment_ratio_utils.put(key=triple.constraint,
                                        value={'activation_count': 1, 'fulfillment_count': 0})

    @staticmethod
    def update_fulfillment_ratio(fulfillment_ratio_utils, triple: Token) -> None:
        metrics = fulfillment_ratio_utils.get(key=triple.constraint)
        fulfillment_ratio_utils.put(key=triple.constraint,
                                    value={'activation_count': metrics['activation_count'],
                                           'fulfillment_count': metrics['fulfillment_count'] + 1})

    @staticmethod
    def get_prefix(items: List[str], constraint_activation: str) -> List[str]:
        indices = [i for i, item in enumerate(items) if item == constraint_activation]

        if len(indices) > 0:
            start_idx = indices[-1]
            sliced = copy.deepcopy(items[start_idx:])
            return sliced
        else:
            return items

    def move_automaton(self, activity: str, constraint_state: Dict, trace_id: str):
        symbol: Dict[str, bool] = self.get_symbol(activity.split("_")[0])
        current_state: Set = self.get_current_state(constraint_state)
        next_state: Set = self.compute_next_state(current_state, symbol)
        self.update_constraint_state(constraint_state, next_state, trace_id)

    @staticmethod
    def map_activity_to_placeholder(current_activity: str, current_constraint: Constraint) -> str:
        activity: str = current_activity.split('_')[0]
        if activity == current_constraint.first_activity:
            return 'a'
        elif activity == current_constraint.second_activity:
            return 'b'
        else:
            return activity.lower()

    def compute_next_state(self, current_state: Set, symbol: Dict[str, bool]) -> Set:
        return reduce(set.union, map(lambda x: self.dfa.get_successors(x, symbol), current_state), set(), )

    def get_symbol(self, activity: str) -> Dict[str, bool]:
        key: str = activity if activity in (self.activation, self.target) else activity.lower()
        return {key: True}

    @staticmethod
    def cleanup_violations_at_trace_end(constraint_instances: MapState, trace_id: str):
        violations: List[Tuple[Token, Dict]] = []
        to_remove: List[Token] = []

        for token, state in constraint_instances.items():
            if token.trace_id == trace_id:
                state['color'] = AutomatonColor.PERMANENTLY_VIOLATED
                violations.append((token, state))
                to_remove.append(token)

        for token in to_remove:
            constraint_instances.remove(token)

        return violations

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}(\n"
            f"  DFA States: {len(self.dfa.states)}\n"
            f"  Initial State: {self.dfa.initial_state}\n"
            f"  Accepting States: {self.dfa.accepting_states}\n"
            f"  Transitions: {self.dfa.get_transitions()}\n"
            f")"
        )
