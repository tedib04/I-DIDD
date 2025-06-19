from typing import List

from pyflink.datastream import FlatMapFunction

from processor.src.utils.types import ConstraintEventPair


class ConstraintExpander(FlatMapFunction):
    def flat_map(self, event):
        CONSTRAINTS: List[str] = [
            'Response',
            'Precedence',
            'Chain Response',
            'Chain Precedence',
            'Alternate Response',
            'Alternate Precedence',
            'Responded Existence',
        ]

        for constraint in CONSTRAINTS:
            pair: ConstraintEventPair = {'constraint': constraint,
                                         'event': event['event'],
                                         'before_in_trace': event['before_in_trace']}

            yield pair
