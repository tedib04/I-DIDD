from typing import List, Tuple, Set, Iterable

from pyflink.datastream import ProcessWindowFunction

from processor.src.utils.declare_model_builder import DeclareModelBuilder
from processor.src.utils.types import Constraint


class DeclareModelAggregator(ProcessWindowFunction):

    def process(self, key, context, elements):
        unique_constraints: List[Tuple[str, str, str, str]] = self.deduplicate_constraints(elements)
        DeclareModelBuilder(constraints=unique_constraints, wrap_width=15).generate_model()
        print('Generated Declare Model successfully!')
        return []

    @staticmethod
    def deduplicate_constraints(constraint_record: Iterable[dict]) -> List[Tuple[str, str, str, str]]:
        seen: Set[Tuple[str, str, str, str]] = set()
        unique_constraints: List[Tuple[str, str, str, str]] = []

        for record in constraint_record:
            constraint: Constraint = record['Constraint']
            data_condition: str = record['Data Condition']
            key: Tuple[str, str, str, str] = (constraint.name,
                                              constraint.first_activity,
                                              constraint.second_activity,
                                              data_condition)
            if constraint not in seen:
                seen.add(key)
                unique_constraints.append(key)

        return unique_constraints
