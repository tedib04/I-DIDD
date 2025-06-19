from pyflink.common import Types
from pyflink.datastream import ProcessFunction, KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import ValueState, ValueStateDescriptor, ListStateDescriptor, ListState


class LogMetricsCalculator(ProcessFunction):
    def __init__(self):
        self.event_counter = 0
        self.log_start_timestamp = None
        self.log_end_timestamp = None
        self.seen_trace_id = set()
        self.counter_trace_id = 0

    def process_element(self, event, ctx: ProcessFunction.Context):
        self.event_counter += 1
        self.update_log_timestamps(event['time_timestamp'])
        self.update_trace_counter(event['case_concept_name'])

        yield {
            'Event_counter': self.event_counter,
            'Log_start_timestamp': self.log_start_timestamp,
            'Log_end_timestamp': self.log_end_timestamp,
            'Counter_trace_id': self.counter_trace_id,
        }

    def update_trace_counter(self, trace_id):
        if trace_id not in self.seen_trace_id:
            self.counter_trace_id += 1
            self.seen_trace_id.add(trace_id)

    def update_log_timestamps(self, event_timestamp):
        if self.log_start_timestamp is None:
            self.log_start_timestamp = event_timestamp
        if self.log_end_timestamp is None:
            self.log_end_timestamp = event_timestamp
        else:
            self.log_start_timestamp = min(self.log_start_timestamp, event_timestamp)
            self.log_end_timestamp = max(self.log_end_timestamp, event_timestamp)


class ActivityOccurrenceTracker(KeyedProcessFunction):
    def __init__(self):
        self.activity_counter = None
        self.activity_in_trace = None

    def open(self, ctx: RuntimeContext):
        self.activity_counter: ValueState = ctx.get_state(ValueStateDescriptor('activity_counter', Types.INT()))
        self.activity_in_trace: ListState = ctx.get_list_state(ListStateDescriptor('activity_in_trace', Types.STRING()))

    def process_element(self, event, ctx: KeyedProcessFunction.Context):
        current_count: int = (self.activity_counter.value() or 0) + 1
        self.activity_counter.update(current_count)

        trace_id: str = event['case_concept_name']
        activities_in_trace = set(self.activity_in_trace.get() or [])

        if trace_id not in activities_in_trace:
            self.activity_in_trace.add(trace_id)

        yield {
            'Activity': ctx.get_current_key(),
            'Frequency': current_count,
            'Trace_count': len(list(activities_in_trace)) + 1
        }
