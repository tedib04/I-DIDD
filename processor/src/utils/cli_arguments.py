import os
from argparse import Namespace, ArgumentParser

from dotenv import load_dotenv


class ProcessorArgumentsParser:

    @staticmethod
    def parse_arguments() -> Namespace:
        load_dotenv()
        parser: ArgumentParser = ArgumentParser(description='Apache Flink processor')
        parser.add_argument('--bootstrap-servers', default='localhost:29092', help='bootstrap servers', type=str)
        parser.add_argument("--event-log", type=str, default=os.getenv("EVENT_LOG"),
                            required=(os.getenv("EVENT_LOG") is None),
                            help="Path to the XES event log to stream into Kafka")
        parser.add_argument('--schema-registry-url', default='http://localhost:8085/', help='schema registry', type=str)
        parser.add_argument('--rewind', help='rewind to begin of process mining data stream', action='store_true')
        parser.add_argument("--dry-run", help="print to stdout instead of writing to Kafka", action="store_true")
        parser.add_argument("--ui-port", default=8081, type=int, help="enables Flink UI at specified port")
        parser.add_argument('--apriori-min-support', type=float, default=os.getenv("APRIORI_MIN_SUPPORT"),
                            required=(os.getenv("APRIORI_MIN_SUPPORT") is None),
                            help='Minimum support threshold for candidate generation')
        parser.add_argument('--input-topic', type=str, default='raw-process-events', help='Name of the input topic')
        parser.add_argument('--output-topic', type=str, default='dashboard-result', help='Name of the output topic')
        args: Namespace = parser.parse_args()
        print("Command line arguments for processor have been parsed successfully.")

        return args
