import json
from pathlib import Path
from typing import Dict

from processor.src.utils.types import Constraint


class FileManager:

    @staticmethod
    def save_result(record: Dict[str, Constraint | float | int], file_path: Path) -> None:
        with open(file=file_path, mode='a') as f:
            f.write(json.dumps({
                'Constraint': record['Constraint'].__str__(),
                'Data Condition': record['Data Condition'],
                '# Activations No Data': record['# Activations No Data'],
                'Fulfilment Ratio No Data': record['Fulfilment Ratio No Data'],
                '# Activations Data': record['# Activations Data'],
                'Fulfilment Ratio Data': record['Fulfilment Ratio Data']
            }) + "\n")
