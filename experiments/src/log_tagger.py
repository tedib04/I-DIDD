import sys

from pm4py import read_xes
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from pm4py.objects.log.obj import EventLog


def tag_end_event(log: EventLog):
    for trace in log:
        num_events = len(trace)
        for idx, event in enumerate(trace):
            event["is_end_event"] = bool(idx == num_events - 1)
    return log


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.xes> <output.xes>")
        sys.exit(1)
    input_file, output_file = sys.argv[1], sys.argv[2]
    log = read_xes(file_path=input_file, return_legacy_log_object=EventLog)
    tagged_log = tag_end_event(log)
    xes_exporter.apply(log=tagged_log, output_file_path=output_file)
