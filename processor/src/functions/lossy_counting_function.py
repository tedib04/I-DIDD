from math import ceil

from pm4py.objects.log.obj import Event
from pyflink.common import Types
from pyflink.datastream import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import MapStateDescriptor, MapState


class LossyCounting(KeyedProcessFunction):

    def __init__(self, epsilon: float = 0.2) -> None:
        self.seen_activities = None
        self.N = None
        self.w = None
        self.countState = None
        self.deltaState = None
        self.epsilon = epsilon

    def open(self, ctx: RuntimeContext) -> None:
        self.seen_activities: MapState = ctx.get_map_state(
            MapStateDescriptor("seen_activities", Types.STRING(), Types.PICKLED_BYTE_ARRAY()))
        self.N = 0
        self.w = ceil(1.0 / self.epsilon)
        self.countState: MapState[str, int] = ctx.get_map_state(
            MapStateDescriptor("countState", Types.STRING(), Types.INT()))
        self.deltaState: MapState[str, int] = ctx.get_map_state(
            MapStateDescriptor("deltaState", Types.STRING(), Types.INT()))

    def process_element(self, event: Event, ctx: KeyedProcessFunction.Context):
        trace_id: str = event['case_concept_name']
        activity_name: str = event['concept_name']

        if self.seen_activities.get(key=trace_id) is None:
            self.seen_activities[trace_id] = [activity_name]
        else:
            self.seen_activities[trace_id].append(activity_name)

        self.N += 1
        b_current: int = ceil(self.N / self.w)

        frequency = self.countState.get(trace_id)
        if frequency is None:
            # first time: f=1, Δ=b_current-1
            self.countState.put(trace_id, 1)
            self.deltaState.put(trace_id, b_current - 1)
        else:
            self.countState.put(trace_id, frequency + 1)
            yield {
                'event': event,
                'before_in_trace': self.seen_activities.get(trace_id)
            }

        # Pruning
        if self.N % self.w == 0:
            to_remove = []
            for trace_id in self.countState.keys():
                f_i = self.countState.get(trace_id)
                delta_i = self.deltaState.get(trace_id)
                if f_i + delta_i <= b_current:
                    to_remove.append(trace_id)

            for trace_id in to_remove:
                self.countState.remove(trace_id)
                self.deltaState.remove(trace_id)

        # Remove history after having finished processing the last event of the trace
        if event['is_end_event']:
            self.seen_activities.remove(key=trace_id)