#!/usr/bin/env python

import logging
from logging import Logger
from time import sleep
from typing import List

from confluent_kafka import Producer, KafkaException, OFFSET_BEGINNING, OFFSET_END
from confluent_kafka.admin import NewTopic, AdminClient


class KafkaTopicSetuper:
    @staticmethod
    def setup_topic(topic: str,
                    logger: Logger,
                    bootstrap_servers: str = 'localhost:29092',
                    num_partitions: int = 1,
                    replication_factor: int = 1,
                    num_attempts: int = 10):

        client: AdminClient = AdminClient({'bootstrap.servers': bootstrap_servers})
        template: str = f'topic {topic} with {num_partitions} partitions and replication factor {replication_factor}'
        topic_desc_new: str = template.format(topic=topic, np=num_partitions, rf=replication_factor)
        topic_desc_old: str = 'none'

        for i in range(num_attempts):
            try:
                # Try to create the topic with the desired configuration (# partitions)
                topics: List[NewTopic] = [
                    NewTopic(topic=topic, num_partitions=num_partitions, replication_factor=replication_factor)]
                futures = client.create_topics(new_topics=topics)  # async operation
                futures[topic].result()  # wait for operation to complete
                logger.debug(f'Created {topic_desc_new}')
                return True  # signal topic created

            except KafkaException:
                # The topic may already exist: check if its configuration matches the desired one
                t = client.list_topics().topics.get(topic)
                if t is not None:
                    np = len(t.partitions)
                    rf = len(t.partitions[0].replicas) if np > 0 else 0
                    topic_desc_old = template.format(topic=t, np=np, rf=rf)
                    if num_partitions == np and replication_factor == rf:
                        logger.debug(f'Found {topic_desc_new}')
                        return False  # signal topic already exists

            sleep(1.0)  # wait between attempts

        raise Exception(f'Expected to find/create {topic_desc_new}, found {topic_desc_old}')

    @staticmethod
    def delete_topic(topic, bootstrap_servers='localhost:29092') -> None:
        client: AdminClient = AdminClient({'bootstrap.servers': bootstrap_servers})
        logging.debug(f'Attempting to delete topic {topic}...')

        futures = client.delete_topics([topic], operation_timeout=30)
        for t, future in futures.items():
            try:
                future.result()  # wait for deletion to complete
                logging.debug(f'Topic {t} deleted successfully.')
            except Exception as e:
                logging.error(f'Failed to delete topic {t}: {e}')

    @staticmethod
    def delete_consumer_group(group_id, bootstrap_servers='localhost:29092'):
        client: AdminClient = AdminClient({'bootstrap.servers': bootstrap_servers})
        logging.debug(f'Attempting to delete consumer group {group_id}...')

        futures = client.delete_consumer_groups(group_ids=[group_id], operation_timeout=30)
        for grp, future in futures.items():
            try:
                future.result()  # Wait for deletion to complete
                logging.debug(f'Consumer group {grp} deleted successfully.')
            except Exception as e:
                logging.error(f'Failed to delete consumer group {grp}: {e}')

    @staticmethod
    def on_assign_seek(before_end=None, after_start=None):
        def on_assign_callback(consumer, partitions):

            for p in partitions:

                # Want to read from end of partition - seek_before_end
                if before_end is not None:
                    p.offset = OFFSET_END  # this resolves to last offset + 1 in partition
                    if before_end != 0:  # if want something after, must compute offset ourselves
                        bounds = consumer.get_watermark_offsets(p)
                        p.offset = max(bounds[0], bounds[1] - before_end)

                # Want to read from start of partition + seek_after_start
                elif after_start is not None:
                    p.offset = OFFSET_BEGINNING  # this resolves to first offset in partition
                    if after_start != 0:  # if want something after, must compute offset ourselves
                        bounds = consumer.get_watermark_offsets(p)
                        p.offset = min(bounds[1], bounds[0] + after_start)

                logging.debug(f'Assigned {p}')  # log partition ID and offset

            consumer.assign(partitions)  # update partition assignments

        return on_assign_callback

    @staticmethod
    def produce_or_block(producer: Producer, **kwargs):
        while True:
            try:
                producer.produce(**kwargs)
                break
            except BufferError:
                producer.flush(1.0)
