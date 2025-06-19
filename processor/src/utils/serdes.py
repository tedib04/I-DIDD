from json import dumps
from typing import Dict, Any

from dateutil.parser import parse
from pm4py.objects.log.obj import Event
from pyflink.common import Row


class SerDes:
    @staticmethod
    def serialize(record: Row) -> str:
        return dumps(record, default=str)

    @staticmethod
    def deserialize(record: Row) -> Event:
        dictionary: Dict[str: Any] = record.as_dict()
        dictionary['concept_name'] = dictionary.pop('concept_name', '')
        dictionary['case_concept_name'] = dictionary.pop('case_concept_name', '')
        dictionary['time_timestamp'] = dictionary.pop('time_timestamp', '')

        if 'time_timestamp' in dictionary:
            dictionary['time_timestamp'] = parse(dictionary['time_timestamp'])

        for key, value in dictionary.pop('eventAttributes', {}).items():
            try:
                converted_value = float(value)
            except ValueError:
                if value.lower() in {'true', 'false'}:
                    converted_value = value.lower() == 'true'
                else:
                    converted_value = value

            dictionary[key] = converted_value

        return Event(dictionary)
