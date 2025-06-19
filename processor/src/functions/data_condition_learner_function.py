from pyflink.common import Types
from pyflink.datastream import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import ValueStateDescriptor, ValueState
from river import compose
from river.metrics import F1
from river.preprocessing import OrdinalEncoder
from river.tree import HoeffdingAdaptiveTreeClassifier

from processor.src.utils.tree_rule_extractor import DecisionRuleExtractor


class DataConditionLearner(KeyedProcessFunction):
    def __init__(self) -> None:
        self.state = None

    def open(self, ctx: RuntimeContext) -> None:
        self.state: ValueState = ctx.get_state(
            state_descriptor=ValueStateDescriptor(name='state', value_type_info=Types.PICKLED_BYTE_ARRAY()))

    def process_element(self, entry, ctx: KeyedProcessFunction.Context):

        if not self.state.value():
            pipeline = compose.Pipeline(
                OrdinalEncoder(),
                HoeffdingAdaptiveTreeClassifier(max_depth=4, binary_split=True, remove_poor_attrs=True),
            )
            metric = F1()
            self.state.update({'pipeline': pipeline, 'metric': metric})

        # Prepare features and label
        features = {k: v for k, v in entry['event'].items() if
                    k not in {'case_concept_name', 'concept_name', 'time_timestamp', 'is_end_event'}}
        label = 1 if entry['is_fulfilled'] else 0

        # Evaluate and update model
        pipeline = self.state.value()['pipeline']
        model = pipeline['HoeffdingAdaptiveTreeClassifier']
        metric = self.state.value()['metric']
        predicted_label = model.predict_one(features)
        metric.update(y_true=label, y_pred=predicted_label)
        model.learn_one(features, label)

        # Persist updated state
        self.state.update({'pipeline': pipeline, 'metric': metric})

        # Extract and emit results once the model has more than 1 node, the tree is balanced, and it has at least 1 leaf node with the fulfillment label.
        if self.state.value()['pipeline']['HoeffdingAdaptiveTreeClassifier'].n_nodes > 1:
            fulfillment_rules, samples = DecisionRuleExtractor().get_fulfillment_rules(
                node=self.state.value()['pipeline']['HoeffdingAdaptiveTreeClassifier']._root)

            if fulfillment_rules and DecisionRuleExtractor.check_tree_is_balanced(samples):
                best_fulfillment_rule: str = max(fulfillment_rules, key=lambda r: r['probability'])['rule']
                yield {
                    'Constraint': entry['constraint'],
                    'Data Condition': best_fulfillment_rule,
                    '# Activations No Data': entry['# Activations No Data'],
                    'Fulfilment Ratio No Data': entry['Fulfilment Ratio No Data']
                }
