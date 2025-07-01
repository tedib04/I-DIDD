import time
from argparse import Namespace
from itertools import count
from pathlib import Path

import dateutil.parser
from pandas import DataFrame
from streamlit import set_page_config, markdown, title, metric, columns, empty, cache_resource

from utils.cli_arguments import FrontendArgumentsParser
from utils.custom_styles import style_sheet
from utils.dashboard_utils import DashboardUtils
from utils.provider import DataProvider


class ProcessDashboardApp:

    def __init__(self, args: Namespace) -> None:
        self.args: Namespace = args
        self.DECLARE_IMG_PATH: Path = Path(self.args.graphviz_declare) / 'declare_model.png'

    def run(self):
        # Set up Streamlit page configuration
        set_page_config(page_title='I-DIDD Dashboard', layout='wide', initial_sidebar_state='expanded')
        title('I-DIDD Dashboard')
        markdown(style_sheet, unsafe_allow_html=True)

        # Get data provider
        provider: DataProvider = get_data_provider(self.args.bootstrap_servers,
                                                   self.args.group_id,
                                                   self.args.input_topic)

        # Initialize metrics display
        metrics = DashboardUtils.initialize_metrics()
        DashboardUtils.display_initial_metrics(metrics)

        # Initialize barchart display
        left_barchart_column, right_barchart_column = columns(2)
        barchart_placeholder_frequency = DashboardUtils.initialize_barchart(barchart_column=left_barchart_column,
                                                                            placeholder_title='Frequency',
                                                                            x_column_title='Frequency')
        barchart_placeholder_in_trace = DashboardUtils.initialize_barchart(barchart_column=right_barchart_column,
                                                                           placeholder_title='Trace_count',
                                                                           x_column_title='Trace_count')

        # Create a new row with two columns for the Declare Model Image and Data-Aware DECLARE Models table
        declare_model_image_column, declare_models_table_column = columns([1, 1], gap='small')

        # Initialize empty Data-Aware DECLARE table
        with declare_model_image_column:
            metric(label='📈Current 10 DATA-AWARE DECLARE Models', value='')
            declare_model_image = declare_model_image_column.plotly_chart(
                figure_or_data=DashboardUtils.create_bar_chart(data=DataFrame(columns=['Activity', 'Frequency']),
                                                               title='Loading ...',
                                                               x_column_title='Frequency'), use_container_width=True)

        # Initialize empty Data-Aware DECLARE figure
        with declare_models_table_column:
            metric(label='🔍 Data-Aware DECLARE Models Explorer', value='')
            declare_models_data: DataFrame = DataFrame(columns=['Constraint', 'Data Condition', '# Activations No Data',
                                                                'Fulfilment Ratio No Data', '# Activations Data',
                                                                'Fulfilment Ratio Data'])

            placeholder_declare_table = empty()
            placeholder_declare_table.dataframe(data=DashboardUtils.style_ratios(declare_models_data),
                                                height=450,
                                                hide_index=True,
                                                use_container_width=True)

        for _ in count():
            # Get statistics and activity frequency data from data provider
            dashboard_statistics: DataFrame = provider.get_dashboard_statistics_data()
            dashboard_barchart = provider.get_dashboard_barchart_data()
            declare_models_table = provider.get_declare_data()

            # Update metrics display if statistics data is available
            if not dashboard_statistics.empty:
                values = [
                    int(dashboard_statistics['Counter_trace_id'].iloc[0]),
                    int(dashboard_statistics['Event_counter'].iloc[0]),
                    dateutil.parser.parse(dashboard_statistics['Log_start_timestamp'].iloc[0]).strftime(
                        '%H:%M:%S %d-%m-%Y'),
                    dateutil.parser.parse(dashboard_statistics['Log_end_timestamp'].iloc[0]).strftime(
                        '%H:%M:%S %d-%m-%Y')
                ]
                DashboardUtils.update_metrics(metrics, values)

            # Update activity frequency data and display bar charts if available
            if not dashboard_barchart.empty:
                DashboardUtils.update_activity_frequency(data=dashboard_barchart,
                                                         chart_placeholder=barchart_placeholder_frequency,
                                                         title='ACTIVITY FREQUENCY',
                                                         x_column='Frequency')
                DashboardUtils.update_activity_frequency(data=dashboard_barchart,
                                                         chart_placeholder=barchart_placeholder_in_trace,
                                                         title='ACTIVITY IN TRACES',
                                                         x_column='Trace_count')

            # Display DECLARE MODEL if available
            if self.DECLARE_IMG_PATH.exists():
                DashboardUtils.update_declare_models(declare_model_path=self.DECLARE_IMG_PATH,
                                                     declare_model_placeholder=declare_model_image)

            # Update Data-Aware DECLARE Models if available
            if not declare_models_table.empty:
                placeholder_declare_table.dataframe(data=DashboardUtils.style_ratios(declare_models_table),
                                                    height=450,
                                                    hide_index=True,
                                                    use_container_width=True)

            time.sleep(0.8)


@cache_resource
def get_data_provider(bootstrap_servers, group_id, input_topic) -> DataProvider:
    provider: DataProvider = DataProvider(bootstrap_servers, group_id, input_topic)
    provider.run()
    return provider


if __name__ == '__main__':
    ProcessDashboardApp(args=FrontendArgumentsParser.parse_arguments()).run()
