import os
from argparse import Namespace, ArgumentParser

from dotenv import load_dotenv


class ProducerArgumentsParser:

    @staticmethod
    def parse_arguments() -> Namespace:
        load_dotenv()
        parser: ArgumentParser = ArgumentParser(description='Kafka producer for Process Executions in XES Standard')
        parser.add_argument('--bootstrap-servers', default='localhost:29092', help='bootstrap servers', type=str)
        parser.add_argument('--event-log', type=str, default=os.getenv('EVENT_LOG'),
                            required=(os.getenv('EVENT_LOG') is None),
                            help='Path to the XES event log to stream into Kafka')
        parser.add_argument('--schema-registry-url', default='http://localhost:8085/', help='schema registry', type=str)
        parser.add_argument('--topic', default='raw-process-events', help='topic name', type=str)
        parser.add_argument('--num-partitions', default=1, help='number of partitions', type=int)
        parser.add_argument('--replication-factor', default=1, help='replication factor', type=int)
        parser.add_argument('--dry-run', help='send to standard output instead of Kafka', action='store_true')
        args: Namespace = parser.parse_args()
        print('Command line arguments parsed successfully.')

        return args
