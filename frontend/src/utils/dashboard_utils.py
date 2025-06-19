import time
from pathlib import Path

import plotly.express as px
import streamlit as st
from PIL import Image, UnidentifiedImageError
from pandas import DataFrame
from streamlit_js_eval import streamlit_js_eval


class DashboardUtils:

    @staticmethod
    def create_bar_chart(data, title, x_column_title):
        fig = px.bar(data_frame=data.sort_values(by=x_column_title, ascending=False),
                     x=x_column_title, y='Activity', orientation='h', color='Activity',
                     title=title, color_discrete_sequence=px.colors.qualitative.Set1, )

        fig.update_layout(
            title_x=0.5, title=dict(text=title, font=dict(size=27), xanchor='center'),
            xaxis=dict(showgrid=True, linecolor='rgb(200,200,200)'),
            yaxis=dict(linecolor='rgb(200,200,200)', tickfont=dict(size=12))
        )
        fig.update_layout({'uirevision': 'foo'}, overwrite=True)
        fig.update_traces(showlegend=False, marker=dict(line=dict(width=0.5, color='black')))

        return fig

    @staticmethod
    def initialize_barchart(barchart_column, placeholder_title, x_column_title):
        barchart_placeholder = barchart_column.empty()
        barchart_placeholder.plotly_chart(
            figure_or_data=DashboardUtils.create_bar_chart(data=DataFrame(columns=['Activity', placeholder_title]),
                                                           title='Loading ...',
                                                           x_column_title=x_column_title), use_container_width=True)
        return barchart_placeholder

    @staticmethod
    def initialize_metrics():
        return [{'label': label, 'value': 'Loading...'} for label in
                ['TRACES', 'EVENTS', 'START TIMESTAMP', 'END TIMESTAMP']]

    @staticmethod
    def update_activity_frequency(data, chart_placeholder, title, x_column):
        chart_placeholder.plotly_chart(
            figure_or_data=DashboardUtils.create_bar_chart(data=data, title=title, x_column_title=x_column),
            use_container_width=True)

    @staticmethod
    def update_metrics(metrics, values):
        for metric, value in zip(metrics, values):
            metric['element'].metric(label=metric['label'], value=value)

    @staticmethod
    def display_initial_metrics(metrics):
        for metric, col in zip(metrics, st.columns(4, gap='small')):
            metric['element'] = col.metric(label=metric['label'], value=metric['value'])

    @staticmethod
    def update_declare_models(declare_model_path, declare_model_placeholder):
        declare_model_img = DashboardUtils.load_image_with_retries(path=declare_model_path)
        if declare_model_img:
            fig = px.imshow(declare_model_img)
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                height=450,
                autosize=True
            )

            fig.update_xaxes(showspikes=True, spikecolor='lightgrey', spikethickness=1, spikedash='dot',
                             visible=False)
            fig.update_yaxes(showspikes=True, spikecolor='lightgrey', spikethickness=1, spikedash='dot',
                             visible=False)

            config = {
                'scrollZoom': True,
                'responsive': True,
                'displayModeBar': True,
                'displaylogo': False,
            }

            declare_model_placeholder.plotly_chart(
                figure_or_data=fig,
                use_container_width=True,
                config=config,
                key="declare_model_chart"
            )

    @staticmethod
    def load_image_with_retries(path: Path, max_retries: int = 5, delay: float = 0.6) -> Image.Image | None:
        last_size = -1
        retries = 0

        while retries < max_retries:
            try:
                size = path.stat().st_size
                if size == 0 or size != last_size:
                    last_size = size
                    raise UnidentifiedImageError('File not yet stable or empty')

                with Image.open(path) as img:
                    img.verify()
                img = Image.open(path)
                img.load()
                return img
            except (UnidentifiedImageError, OSError):
                retries += 1
                time.sleep(delay)
                if retries > max_retries:
                    streamlit_js_eval(js_expressions='parent.window.location.reload()')
        return None

    @staticmethod
    def style_ratios(df: DataFrame) -> DataFrame.style:
        styler = (
            df.style
            .background_gradient(
                subset=['Fulfilment Ratio No Data', 'Fulfilment Ratio Data'],
                cmap='Purples',
                low=0, high=1
            )
        )

        table_styles = [
            {
                'selector': '',
                'props': [
                    ('padding-top', '0.5px'),
                    ('padding-right', '0.5px'),
                    ('padding', '10px 10px'),
                    ('height', '458px !important'),
                    ('width', '100%'),
                    ('font-size', '45px'),
                ]
            },
            {
                'selector': 'th',
                'props': [
                    ('text-align', 'center !important'),
                    ('padding', '15px 10px'),
                    ('border', '1px solid #ddd'),
                    ('background-color', '#6c5ce7'),
                    ('color', 'white'),
                    ('font-weight', 'bold')
                ]
            }, {
                'selector': 'tr:hover',
                 'props': [
                     ('background-color', '#ddd')
                 ]

            }
        ]

        return styler.set_table_styles(table_styles)