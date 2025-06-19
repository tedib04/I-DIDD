#!/usr/bin/env python3
from pathlib import Path
from typing import Dict

from pyflink.common import Types
from pyflink.datastream.functions import KeyedCoProcessFunction, RuntimeContext
from pyflink.datastream.state import ValueStateDescriptor, ValueState, ListStateDescriptor, ListState

from processor.src.utils.file_manager import FileManager
from processor.src.utils.types import Constraint


class DataAwareMetricsEvaluator(KeyedCoProcessFunction):

    def __init__(self, event_log:str):
        self.activations = None
        self.activation_count_data = None
        self.fulfilment_count_data = None
        self.event_log:str = event_log
        self.RULES_DISCOVERY_FILE_PATH: Path = Path(__file__).parents[
                                                   3] / f'experiments/results/rules_{self.event_log}.jsonl'

    def open(self, ctx: RuntimeContext) -> None:
        self.activations: ListState = ctx.get_list_state(ListStateDescriptor('activations', Types.PICKLED_BYTE_ARRAY()))
        self.activation_count_data: ValueState = ctx.get_state(
            ValueStateDescriptor('data_activation_count', Types.LONG()))
        self.fulfilment_count_data: ValueState = ctx.get_state(
            ValueStateDescriptor('data_fulfilment_count', Types.LONG()))

    def process_element1(self, activation, ctx: KeyedCoProcessFunction.Context):
        self.activations.add(activation)

    def process_element2(self, learned_conditions, ctx: KeyedCoProcessFunction.Context):
        data_condition: str = learned_conditions['Data Condition']
        constraint: Constraint = learned_conditions['Constraint']

        activation_count_no_data: float = learned_conditions['# Activations No Data']
        fulfilment_ratio_no_data: float = learned_conditions['Fulfilment Ratio No Data']

        for activation in self.activations:
            is_data_aware_activation: bool = self.is_data_condition_satisfied(activation, data_condition)
            # If condition is not satisfied, then it is not a valid DATA-AWARE ACTIVATION, but was simply a normal CONTROL FLOW ACTIVATION.
            if not is_data_aware_activation:
                continue

            self.activation_count_data.update((self.activation_count_data.value() or 0) + 1)
            if activation['is_fulfilled']:
                self.fulfilment_count_data.update((self.fulfilment_count_data.value() or 0) + 1)

        record: Dict[str, Constraint | str | float] = self.construct_result_record(constraint, data_condition,
                                                                                   activation_count_no_data,
                                                                                   fulfilment_ratio_no_data)
        FileManager.save_result(record=record, file_path=self.RULES_DISCOVERY_FILE_PATH)
        self.activations.clear()

        yield record

    def construct_result_record(self, constraint: Constraint, data_condition: str, activation_count_no_data: float,
                                fulfilment_ratio_no_data: float) -> Dict[str, Constraint | str | float]:
        return {'Constraint': constraint,
                'Data Condition': data_condition,
                '# Activations No Data': activation_count_no_data,
                'Fulfilment Ratio No Data': fulfilment_ratio_no_data,
                '# Activations Data': self.activation_count_data.value() or 0,
                'Fulfilment Ratio Data': f'{self.calculate_fulfilment_ratio():.3f}'}

    def calculate_fulfilment_ratio(self) -> float:
        activation_count = self.activation_count_data.value() or 0
        fulfilment_count = self.fulfilment_count_data.value() or 0

        if activation_count == 0:
            return 0.0
        return fulfilment_count / activation_count

    @staticmethod
    def is_data_condition_satisfied(activation, data_condition: str) -> bool:
        try:
            is_data_aware_activation: bool = bool(
                eval(data_condition, {}, {k: v for k, v in activation['event'].items()}))
        except NameError:
            # if the attribute condition is for an attribute not inside the event payload
            is_data_aware_activation = True
        return is_data_aware_activation
