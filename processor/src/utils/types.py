from typing import TypedDict, List, NamedTuple

from pm4py.objects.log.obj import Event


class Constraint:
    def __init__(self, name: str, first_activity: str, second_activity: str):
        self.name = name
        self.first_activity = first_activity
        self.second_activity = second_activity

    def __str__(self):
        return f"{self.name}[{self.first_activity}, {self.second_activity}]"

    def __eq__(self, other):
        return self.name == other.name and self.first_activity == other.first_activity and self.second_activity == other.second_activity

    def __hash__(self):
        return hash((self.name, self.first_activity, self.second_activity))


class ConstraintEventPair(TypedDict):
    constraint: str
    event: Event
    before_in_trace: List[str]


class Token(NamedTuple):
    constraint: Constraint
    activation: str
    trace_id: str

    def __str__(self):
        return (f"Token(constraint={self.constraint}, "
                f"activation={self.activation}, "
                f"trace_id={self.trace_id})")
