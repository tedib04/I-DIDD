#!/usr/bin/env python
import os
from argparse import Namespace
from pathlib import Path

from pyflink.common import SimpleStringSchema, Types, Configuration
from pyflink.datastream import StreamExecutionEnvironment, DataStream
from pyflink.datastream.connectors import DeliveryGuarantee
from pyflink.datastream.connectors.kafka import KafkaSink, KafkaRecordSerializationSchema
from pyflink.table import StreamTableEnvironment

from processor.src.functions.activation_discovery_function import ControlFlowActivationsDiscoverer
from processor.src.functions.data_aware_metrics_calculator_function import DataAwareMetricsEvaluator
from processor.src.functions.data_condition_learner_function import DataConditionLearner
from processor.src.functions.expander_function import ConstraintExpander
from processor.src.functions.generator_function import FrequentCandidateConstraintGenerator
from processor.src.functions.lossy_counting_function import LossyCounting
from processor.src.functions.statistics_function import LogMetricsCalculator, ActivityOccurrenceTracker
from processor.src.functions.visual_model_builder_function import DeclareModelAggregator
from processor.src.utils.cli_arguments import ProcessorArgumentsParser
from processor.src.utils.filnk_table_manager import FlinkManager
from processor.src.utils.kafka_topic_monitor import wait_for_topics
from processor.src.utils.serdes import SerDes


class FlinkProcessor:
    def __init__(self, args: Namespace, parallelism: int = 1) -> None:
        self.args: Namespace = args
        self.parallelism: int = parallelism
        self.MODEL_PICTURE_PATH: Path = Path(__file__).parents[2] / f'frontend/src/declare_model.png'
        self.KAFKA_CONNECTOR_PATH: str = (
                Path(__file__).parent / 'libs/flink-sql-connector-kafka-3.1.0-1.18.jar').resolve().as_uri()
        self.AVRO_CONNECTOR_PATH: str = (
                Path(__file__).parent / 'libs/flink-sql-avro-confluent-registry-1.18.1.jar').resolve().as_uri()

    def run(self) -> None:
        try:
            # Wait for input Kafka topic
            wait_for_topics(self.args.bootstrap_servers, self.args.input_topic)

            # Configure Flink streaming environment
            env: StreamExecutionEnvironment = self.configure_flink_environment()

            # Create Table API Environment
            tenv: StreamTableEnvironment = StreamTableEnvironment.create(env)
            print('Table API Environment has been successfully created.')

            # Create the Table API SQL Table for deserialization
            FlinkManager.create_kafka_source_table(tenv, self.args)

            # Convert the log table to a DateStream object
            log_stream: DataStream = FlinkManager.table_to_datastream(tenv)

            # Create stream logic
            statistics_stream: DataStream = self.build_statistics_stream(log_stream)
            process_discovery_stream: DataStream = self.build_process_discovery_stream(log_stream).map(SerDes.serialize,
                                                                                                       Types.STRING())

            # Emit to Kafka only if not in dry-run mode
            if not self.args.dry_run:
                # Define a Flink sink to write to Kafka output topic
                sink: KafkaSink = KafkaSink.builder() \
                    .set_bootstrap_servers(self.args.bootstrap_servers) \
                    .set_record_serializer(
                    KafkaRecordSerializationSchema.builder()
                    .set_topic(self.args.output_topic)
                    .set_value_serialization_schema(SimpleStringSchema())
                    .build()
                ) \
                    .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE) \
                    .build()

                # Write results to Kafka
                statistics_stream.sink_to(sink).set_parallelism(self.parallelism)
                process_discovery_stream.sink_to(sink).set_parallelism(self.parallelism)
                statistics_stream.print()
                process_discovery_stream.print()
                print(f'Output stream is set to sink to Kafka topic {self.args.output_topic}.')
            else:
                print('Dry-run mode is enabled. Output stream is printed to stdout instead of writing to Kafka.')
                statistics_stream.print()
                process_discovery_stream.print()

            # Execute the job
            env.execute()
            print('Flink job execution started')

        except KeyboardInterrupt:
            print('User interrupted the program ... Stopping gracefully!')
            if os.path.exists(self.MODEL_PICTURE_PATH):
                os.unlink(self.MODEL_PICTURE_PATH)
                print(f"{self.MODEL_PICTURE_PATH} has been deleted successfully.")
        except Exception as e:
            print(f'An error occurred during the execution of the Flink job: {str(e)}')

    def build_process_discovery_stream(self, log_stream: DataStream) -> DataStream:
        # 1) Track activity history & expand constraints
        expanded_constraints: DataStream = log_stream \
            .key_by(lambda _: "") \
            .process(LossyCounting()) \
            .name("LossyCounting") \
            .uid("LossyCounting") \
            .flat_map(ConstraintExpander()) \
            .name("ConstraintExpander") \
            .uid("ConstraintExpander")

        # 2) Generate candidate constraints
        candidate_constraints: DataStream = expanded_constraints \
            .key_by(lambda x: x['constraint']) \
            .process(FrequentCandidateConstraintGenerator(apriori_min_support=self.args.apriori_min_support)) \
            .name("CandidateConstraintGenerator") \
            .uid("CandidateConstraintGenerator")

        # 3) Discover activations + compute control flow  fulfillment ratio  & activation ratio
        discovered_activations: DataStream = candidate_constraints \
            .key_by(lambda x: (x['constraint'].name, x['constraint'].first_activity, x['constraint'].second_activity)) \
            .process(ControlFlowActivationsDiscoverer()) \
            .name("ControlFlowActivationsDiscoverer") \
            .uid("ControlFlowActivationsDiscoverer")

        # 4) Learn data conditions via Hoeffding Adapting tree
        learned_data_conditions: DataStream = discovered_activations \
            .key_by(lambda x: (x['constraint'].name, x['constraint'].first_activity, x['constraint'].second_activity)) \
            .process(DataConditionLearner()) \
            .name("DataConditionLearner") \
            .uid("DataConditionLearner")

        # 5) Compute data-aware metrics by connecting the leaned results + activations
        data_aware_metrics: DataStream = discovered_activations \
            .connect(learned_data_conditions) \
            .key_by(
            lambda x_1: (
                x_1['constraint'].name,
                x_1['constraint'].first_activity,
                x_1['constraint'].second_activity
            ),
            lambda x_2: (
                x_2['Constraint'].name,
                x_2['Constraint'].first_activity,
                x_2['Constraint'].second_activity
            )) \
            .process(DataAwareMetricsEvaluator(event_log=self.args.event_log)) \
            .name("DataAwareMetricsEvaluator") \
            .uid("DataAwareMetricsEvaluator")

        # 6) Build count window of last 10 computed Declare models
        declare_models: DataStream = data_aware_metrics \
            .key_by(lambda _: '') \
            .count_window(10) \
            .process(DeclareModelAggregator()) \
            .name("DeclareModelAggregator") \
            .uid("DeclareModelAggregator")

        return data_aware_metrics

    @staticmethod
    def build_statistics_stream(log_stream: DataStream) -> DataStream:
        log_metrics: DataStream = log_stream \
            .process(LogMetricsCalculator()) \
            .map(SerDes.serialize, Types.STRING())

        activity_occurrence_tracker: DataStream = log_stream \
            .key_by(lambda x: x['concept_name']) \
            .process(ActivityOccurrenceTracker()) \
            .map(SerDes.serialize, Types.STRING())

        return log_metrics.union(activity_occurrence_tracker)

    def configure_flink_environment(self) -> StreamExecutionEnvironment:
        conf: Configuration = Configuration()
        conf.set_integer('rest.port', self.args.ui_port)
        conf.set_boolean('rest.flamegraph.enabled', True)
        env: StreamExecutionEnvironment = StreamExecutionEnvironment.get_execution_environment(conf)
        env.set_parallelism(self.parallelism)

        env.add_jars(self.KAFKA_CONNECTOR_PATH)
        env.add_jars(self.AVRO_CONNECTOR_PATH)
        print(f'Obtained Flink Kafka connector JAR from: {self.KAFKA_CONNECTOR_PATH}')
        print(f'Obtained SQL Avro connector JAR from: {self.AVRO_CONNECTOR_PATH}')
        print('Flink streaming environment has been configured correctly.')

        return env


if __name__ == '__main__':
    FlinkProcessor(args=ProcessorArgumentsParser.parse_arguments()).run()