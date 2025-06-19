#!/usr/bin/env python
import datetime
import logging
import sys
from argparse import Namespace
from logging import Logger
from pathlib import Path
from time import sleep
from typing import Dict, Optional, List

from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
from pm4py.objects.log.obj import Event
from pm4py.streaming.importer.xes.variants.xes_event_stream import StreamingEventXesReader

from utils.kafak_topic_setupper import KafkaTopicSetuper
from utils.cli_arguments import ProducerArgumentsParser



class KafkaProducer:
    def __init__(self, args: Namespace) -> None:
        self.args: Namespace = args
        self.producer: Optional[Producer] = None
        self.logger: Logger = self.setup_logger()
        self.XES_FILE_PATH: Path = Path('/experiments/data/tagged') / self.args.event_log
        self.AVRO_SCHEMA_PATH: Path = Path(__file__).parent.parent / 'avro/datamodel.avsc'

    def setup_logger(self) -> Logger:
        self.logger: Logger = logging.getLogger('KafkaProducerApp')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        return self.logger

    def create_producer(self) -> Optional[Producer]:
        if self.args.dry_run:
            self.logger.info('Dry-run mode enabled. No Kafka producer will be created.')
            return None
        else:
            KafkaTopicSetuper.setup_topic(topic=self.args.topic, logger=self.logger, bootstrap_servers=self.args.bootstrap_servers,
                        num_partitions=self.args.num_partitions, replication_factor=self.args.replication_factor)
            self.logger.info(
                f'Kafka topic {self.args.topic} setup with {self.args.num_partitions} partitions and {self.args.replication_factor} replication factor.')

            # Create Kafka producer with specified configurations
            config: Dict[str, str] = {'bootstrap.servers': self.args.bootstrap_servers, 'compression.type': 'gzip',
                                      'acks': 'all',  # Wait for leader and replicas to acknowledge
                                      'retries': 5,  # Retry failed produce attempts
                                      'linger.ms': 250,  # Allow some batching
                                      'enable.idempotence': True,  # Ensure safe production in case of retries
                                      }
            producer: Producer = Producer(config)
            self.logger.info('Kafka producer created successfully.')

            return producer

    def run(self) -> None:
        try:
            if not self.args.dry_run:
                self.producer = self.create_producer()

            serializer: AvroSerializer = self.get_message_serializer(args=self.args)
            self.logger.info('Message serializer created successfully.')

            # Get sorted events from the XES file
            events: List[Event] = self.get_sorted_events()
            self.logger.info(f'Total events to process: {len(events)}')

            # Produce Events to Kafka Broker
            for event in events:
                try:
                    # Check if the event is not None and dry run mode is not enabled
                    if event is not None and not self.args.dry_run:
                        # Serialize the message
                        serialized_message: bytes = serializer(event, SerializationContext(topic=self.args.topic,
                                                                                           field=MessageField.VALUE))

                        # Produce the serialized message to Kafka
                        self.create_producer().produce(topic=self.args.topic, key=None, value=serialized_message,
                                                       on_delivery=self.delivery_report)

                        self.logger.info(f'Message produced successfully: {event}')
                    else:
                        self.logger.info(f'Message produced successfully: {event}')

                except Exception as ex:
                    self.logger.error(f'Failed to process event {event}: {ex}', exc_info=True)

                sleep(0.5)  # Delay between events

            self.logger.info('Event processing completed. Waiting for outstanding deliveries...')
            if self.producer:
                self.producer.flush(5.0)

        except Exception as ex:
            self.logger.error(f'An error occurred in run: {ex}', exc_info=True)
        finally:
            if self.producer:
                self.producer.flush(5.0)
                self.logger.info('Kafka producer flushed and closed.')
                self.logger.info('Deleting topics..')

    def get_message_serializer(self, args: Namespace) -> AvroSerializer:
        try:
            avro_schema = Path(self.AVRO_SCHEMA_PATH).read_text()
            self.logger.info(f'Loaded AVRO schema from {self.AVRO_SCHEMA_PATH}')
        except Exception as e:
            self.logger.error(f'Error reading AVRO schema file: {e}', exc_info=True)
            raise

        # Create the Confluent Schema Registry client
        schema_registry: SchemaRegistryClient = SchemaRegistryClient({'url': args.schema_registry_url})
        self.logger.info('Schema Registry client initialized.')

        # Create the Avro Serializer using Schema Registry and Avro Schema
        serializer: AvroSerializer = AvroSerializer(schema_registry_client=schema_registry, schema_str=avro_schema,
                                                    to_dict=self.get_event_attributes)
        self.logger.info('AvroSerializer configured successfully.')

        return serializer

    def get_event_attributes(self, event: Event, ctx: SerializationContext) -> Dict[str, Dict]:
        def sanitize(key: str) -> str:
            return key.replace(':', '_') if ':' in key else key

        standard_keys = [
            'case:concept:name',
            'concept:name',
            'time:timestamp'
        ]

        attributes: Dict[str, str] = {}
        for original_key in standard_keys:
            safe_key = sanitize(original_key)
            value = event.get(original_key)
            if isinstance(value, datetime.datetime):
                attributes[safe_key] = value.isoformat()
            else:
                attributes[safe_key] = str(value) if value is not None else ''

        non_standard: Dict[str, str] = {}
        for key, value in event.items():
            if key in standard_keys:
                continue
            safe_key = sanitize(key)
            non_standard[safe_key] = str(value)

        attributes['eventAttributes'] = non_standard
        return attributes

    def get_sorted_events(self) -> List[Event]:
        try:
            stream_reader: StreamingEventXesReader = StreamingEventXesReader(self.XES_FILE_PATH)
            events: List[Event] = []

            while True:
                message: Optional[Event] = stream_reader.read_event()
                if message is None:
                    break
                events.append(message)
            events.sort(key=lambda x: x['time:timestamp'])
            self.logger.info('Events sorted by timestamp successfully.')
            return events
        except Exception as ex:
            self.logger.error(f'Error reading evens from XES file: {ex}', exc_info=True)
            raise

    def delivery_report(self, error, message) -> None:
        if error:
            self.logger.error(f'Message failed to deliver!')
        else:
            self.logger.info(
                f'Message delivered to Topic={message.topic()} [Partition:{message.partition()}] at offset {message.offset()}')


if __name__ == '__main__':
    KafkaProducer(args=ProducerArgumentsParser.parse_arguments()).run()
