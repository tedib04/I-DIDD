#!/usr/bin/env python
from argparse import Namespace

from pyflink.common import WatermarkStrategy, Duration
from pyflink.common.watermark_strategy import TimestampAssigner
from pyflink.datastream import DataStream
from pyflink.table import StreamTableEnvironment
from pyflink.table import Table

from processor.src.utils.serdes import SerDes


class FlinkManager:

    @staticmethod
    def get_observation_watermark_strategy():
        class ObservationTimestampAssigner(TimestampAssigner):
            def extract_timestamp(self, value, _):
                return int(value["time_timestamp"].timestamp() * 1000)

        return WatermarkStrategy \
            .for_bounded_out_of_orderness(Duration.of_minutes(20)) \
            .with_timestamp_assigner(ObservationTimestampAssigner())

    @staticmethod
    def table_to_datastream(tenv: StreamTableEnvironment) -> DataStream:
        log_table: Table = tenv.from_path(path="log")
        log_stream: DataStream = tenv.to_data_stream(table=log_table) \
            .map(SerDes.deserialize) \
            .assign_timestamps_and_watermarks(FlinkManager.get_observation_watermark_strategy())
        print("Successfully converted 'log' table to data stream.")

        return log_stream

    @staticmethod
    def create_kafka_source_table(tenv: StreamTableEnvironment, args: Namespace) -> None:
        tenv.execute_sql(f"""
                  CREATE TABLE log (
                      `case_concept_name` STRING,
                      `concept_name` STRING,
                      `time_timestamp`  STRING,
                      `eventAttributes` MAP<STRING, STRING>
                  ) WITH (
                      'connector' = 'kafka',
                      'topic' = '{args.input_topic}',
                      'properties.bootstrap.servers' = '{args.bootstrap_servers}',
                      'properties.group.id' = 'flink-group',
                      'scan.startup.mode' = 'earliest-offset',
                      'value.format' = 'avro-confluent',
                      'value.avro-confluent.url' = '{args.schema_registry_url}',
                      'sink.parallelism' ='1'
                  )
                  """)

        print("Kafka source table 'log' has been created successfully for AVRO deserialization.")
