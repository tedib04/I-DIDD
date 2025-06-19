#!/usr/bin/env python

import atexit
from json import loads
from threading import Thread, RLock, Event
from typing import List

from confluent_kafka import Consumer, OFFSET_BEGINNING
from pandas import DataFrame, concat


class DataProvider:

    def __init__(self, bootstrap_servers, group_id, input_topic):
        self.lock = RLock()
        self.thread = None
        self.thread_stop_requested = None
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.statistics = []
        self.activities = []
        self.response = []
        self.input_topic = input_topic

    def get_dashboard_statistics_data(self) -> DataFrame:
        return self.get_dataframe(self.statistics,
                                  columns=['Event_counter', 'Log_start_timestamp',
                                           'Log_end_timestamp', 'Counter_trace_id'])

    def get_dashboard_barchart_data(self) -> DataFrame:
        return self.get_dataframe(self.activities,
                                  columns=['Activity', 'Frequency', 'Trace_count'])

    def get_declare_data(self) -> DataFrame:
        return self.get_dataframe(self.response,
                                  columns=['Constraint', 'Data Condition', '# Activations No Data',
                                           'Fulfilment Ratio No Data', '# Activations Data',
                                           'Fulfilment Ratio Data'])

    def get_dataframe(self, data: List, columns: List[str]) -> DataFrame:
        with self.lock:
            rows = []
            for r in data:
                row = [r[col] for col in columns]
                rows.append(row)
            return DataFrame(rows, columns=columns)

    def run(self) -> None:
        if not self.thread:
            self.thread_stop_requested = Event()
            self.thread = Thread(target=self._run, args=(), daemon=True)
            print('Starting data provider thread.')
            self.thread.start()
            atexit.register(lambda: self.stop())

    def stop(self) -> None:
        if self.thread:
            print('Stopping data provider thread.')
            self.thread_stop_requested.set()
            self.thread.join()
            self.thread = None
            self.thread_stop_requested = None
            pass

    def _run(self) -> None:

        consumer: Consumer = self.create_consumer()
        print('Created consumer.')

        try:
            consumer.subscribe(topics=[self.input_topic], on_assign=self.on_assign_set_offset)
            print('Consumer subscribed.')

            while not self.thread_stop_requested.is_set():
                msg = consumer.poll(0.25)

                if msg is None:
                    continue

                if msg.error():
                    print(f'Consumer error: {msg.error()}.')
                    continue

                data = loads(msg.value())
                self.process_message(data)

        finally:
            consumer.close()
            print('Consumer stopped.')

    def process_message(self, data):
        try:
            with self.lock:
                if 'Event_counter' in data:
                    self.statistics = [data]
                elif 'Activity' in data:
                    self.activities = self.concatenate_df(self.activities, data, subset='Activity')
                elif 'Fulfilment Ratio No Data' in data:
                    self.response = self.concatenate_df(self.response, data)
                else:
                    print(f'Received unknown message {data}.')
        except Exception as e:
            print(f'Error processing message: {e}.')

    def create_consumer(self) -> Consumer:
        try:
            return Consumer({
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': self.group_id,
            })
        except Exception as e:
            print(f'Error creating consumer: {e}')
            raise

    @staticmethod
    def on_assign_set_offset(consumer, partitions):
        for partition in partitions:
            partition.offset = OFFSET_BEGINNING
        consumer.assign(partitions)

    @staticmethod
    def concatenate_df(data_list, new_data, subset=None):
        df_existing: DataFrame = DataFrame(data_list)
        df_new: DataFrame = DataFrame([new_data])
        combined_df = concat([df_existing, df_new]) \
            .drop_duplicates(subset=subset, keep='last') \
            .reset_index(drop=True)

        return combined_df.to_dict('records')
