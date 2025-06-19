from typing import Dict, Tuple

from river.tree.base import Leaf


class DecisionRuleExtractor:

    def get_fulfillment_rules(self, node, current_rule=None, rules=None, samples_nr=None):
        if rules is None:
            rules = []
        if current_rule is None:
            current_rule = []

        if samples_nr is None:
            samples_nr = {'fulfilment': 0, 'violations': 0}

        if isinstance(node, Leaf):
            leaf_label: float = max(node.stats, key=node.stats.get)
            samples_nr['fulfilment'] += node.stats.get(1, 0)
            samples_nr['violations'] += node.stats.get(0, 0)

            if leaf_label == 1:
                rule = " and ".join(current_rule)
                rules.append({
                    "rule": rule,
                    "probability": round(node.stats[1] / sum(node.stats.values()), 2),
                })
        else:
            left, right = node.children

            if left:
                condition = self.parse_condition(node, is_right_child=False)
                self.get_fulfillment_rules(
                    node=left,
                    current_rule=current_rule + [condition],
                    rules=rules,
                    samples_nr=samples_nr
                )

            if right:
                condition = self.parse_condition(node, is_right_child=True)
                self.get_fulfillment_rules(
                    node=right,
                    current_rule=current_rule + [condition],
                    rules=rules,
                    samples_nr=samples_nr
                )

        return rules, samples_nr

    def parse_condition(self, node, is_right_child):
        split: str = node.repr_split

        if '{=, ≠}' in split:
            attribute_name, attribute_value = self.extract_parts(split, '{=, ≠}')
            operator = '!=' if is_right_child else '=='
            attribute_value = self.quote_if_needed(attribute_value)
            return f"{attribute_name} {operator} {attribute_value}"

        elif '≤' in split:
            attribute_name, attribute_value = self.extract_parts(split, '≤')
            operator = '>' if is_right_child else '<='
            attribute_value = self.quote_if_needed(attribute_value)
            return f"{attribute_name} {operator} {attribute_value}"

        return split

    @staticmethod
    def quote_if_needed(value: str) -> str | float:
        try:
            float(value)
            return value
        except ValueError:
            # escape any single‐quotes inside
            safe: str = value.replace("'", "\\'")
            return f"'{safe}'"

    @staticmethod
    def check_tree_is_balanced(samples: Dict, ratio_threshold: int = 1.5) -> bool:
        fulfilment: float = samples.get('fulfilment', 0)
        violations: float = samples.get('violations', 0)

        if fulfilment == 0 or violations == 0:
            return fulfilment == violations

        ir: float = max(fulfilment, violations) / min(fulfilment, violations)
        return ir <= ratio_threshold

    @staticmethod
    def extract_parts(expression: str, operator: str) -> Tuple[str, str | float]:
        attribute_name, _, attribute_value = expression.partition(operator)
        try:
            value: float = round(float(attribute_value.strip()), 2)
        except ValueError:
            value: str = attribute_value.strip()
        return attribute_name.strip(), value
