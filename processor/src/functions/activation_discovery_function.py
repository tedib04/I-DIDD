from typing import Dict, List

from pm4py.objects.log.obj import Event
from pyflink.common import Types
from pyflink.datastream import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import MapStateDescriptor, MapState

from processor.src.utils.types import Constraint


class ControlFlowActivationsDiscoverer(KeyedProcessFunction):

    def __init__(self) -> None:
        self.active_constraints = None
        self.fulfillment_ratio_utils = None

    def open(self, ctx: RuntimeContext) -> None:
        self.active_constraints: MapState = ctx.get_map_state(
            state_descriptor=MapStateDescriptor(name='active_constraints',
                                                key_type_info=Types.PICKLED_BYTE_ARRAY(),
                                                value_type_info=Types.PICKLED_BYTE_ARRAY()))

        self.fulfillment_ratio_utils: MapState = ctx.get_map_state(
            state_descriptor=MapStateDescriptor(name='fulfillment_ratio_utils',
                                                key_type_info=Types.PICKLED_BYTE_ARRAY(),
                                                value_type_info=Types.PICKLED_BYTE_ARRAY()))

    def process_element(self, entry, ctx: KeyedProcessFunction.Context):
        constraint: Constraint = entry['constraint']
        event: Event = entry['event']
        trace_id: str = entry['event']['case_concept_name']
        activity_name: str = entry['activity_name']
        constraint_automaton = entry['automaton']
        seen_target: List[str] = entry['before_in_trace']

        activations = constraint_automaton.process_event(constraint=constraint,
                                                         event=event,
                                                         activity=activity_name,
                                                         trace_id=trace_id,
                                                         active_constraints=self.active_constraints,
                                                         fulfillment_ratio_utils=self.fulfillment_ratio_utils,
                                                         seen_target=seen_target)

        for status, activation_list in activations.items():
            for constraint_activation in activation_list:
                constraint: Constraint = constraint_activation[0][0]
                event: Event = constraint_activation[1]['payload']
                fulfillment_ratio: float = self.compute_fulfillment_ratio(constraint=constraint)
                is_fulfilled: bool = status == 'fulfilling'
                activation_count: int = self.fulfillment_ratio_utils.get(key=constraint)['activation_count']

                yield self.format_output(constraint=constraint,
                                         event=event,
                                         is_fulfilled=is_fulfilled,
                                         ratio=fulfillment_ratio,
                                         activation_count=activation_count)

                yield self.format_output(constraint=self.negate_constraint(constraint=constraint),
                                         event=event,
                                         is_fulfilled=not is_fulfilled,
                                         ratio=1 - fulfillment_ratio,
                                         activation_count=activation_count)

    @staticmethod
    def format_output(constraint: Constraint,
                      event: Event,
                      is_fulfilled: bool,
                      ratio: float,
                      activation_count: float) -> Dict:
        return {
            'constraint': constraint,
            'event': event,
            'is_fulfilled': is_fulfilled,
            'Fulfilment Ratio No Data': float(f'{ratio:.3f}'),
            '# Activations No Data': activation_count
        }

    @staticmethod
    def negate_constraint(constraint: Constraint) -> Constraint:
        return Constraint(
            name=f'Not {constraint.name}',
            first_activity=constraint.first_activity,
            second_activity=constraint.second_activity
        )

    def compute_fulfillment_ratio(self, constraint: Constraint) -> float:
        fulfillment_count: int = self.fulfillment_ratio_utils.get(key=constraint)['fulfillment_count']
        activation_count: int = self.fulfillment_ratio_utils.get(key=constraint)['activation_count']

        return round(fulfillment_count / activation_count, 3)
