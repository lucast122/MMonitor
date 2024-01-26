import dash_core_components as dcc
import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objs as go
from django.db.models import Avg
from django_plotly_dash import DjangoDash

from users.models import SequencingStatistics


class QC:

    def get_data(self):
        stats = SequencingStatistics.objects.filter(user_id=self.user_id)

        if not stats.exists():
            return pd.DataFrame(), None  # Return an empty DataFrame and None if no records are found
        return pd.DataFrame.from_records(stats.values()), stats

    def __init__(self, user_id):
        self.text_style = 'text-primary my-2'
        self.unique_sample_ids = []
        self.stats = None
        self.user_id = user_id
        self.app = DjangoDash('taxonomy', add_bootstrap_links=True)
        self.stats_df, self.stats = self.get_data()

        if self.stats:
            self.sample_name = self.stats.values('sample_name').distinct()
            self.unique_sample_ids = [item['sample_name'] for item in self.sample_name]

        self._init_layout()

    def _init_layout(self):
        indicator_span = 2

        if not self.stats_df.empty:
            qc_layout = dmc.Container([
                dmc.Title("Quality of all samples", align="center", style={"marginBottom": "20px"}),

                dmc.Grid([
                    dmc.Col(dcc.Graph(id='average-read-length-plot', figure=self.get_mean_read_length_plot()), span=12),
                    dmc.Col(
                        dcc.Graph(id='average-read-quality-plot', figure=self.get_aggregated_mean_quality_score_plot()),
                        span=12),
                    dmc.Col(dcc.Graph(figure=self.get_mean_gc_per_sample_plot()),
                            span=12),
                    dmc.Col(dcc.Graph(id='total-bases-sample-plot', figure=self.get_total_bases_sequenced_plot()),
                            span=12),

                ]),

                dmc.Space(h="xl"),
                dmc.Title("Quality of individual samples", align="center", style={"marginBottom": "20px"}),

                dmc.Select(
                    label="Select sample:",
                    id='sample-dropdown-qc',
                    data=[{'label': name, 'value': name} for name in self.unique_sample_ids],
                    value=self.unique_sample_ids[0] if self.unique_sample_ids else None,
                    style={"marginBottom": "20px"}
                ),

                dmc.Grid([
                    dmc.Col(dcc.Graph(id='mean_read_length-graph'), indicator_span),
                    dmc.Col(dcc.Graph(id='mean_quality_score-graph'), indicator_span),
                    dmc.Col(dcc.Graph(id='number_of_reads-graph'), indicator_span),
                    dmc.Col(dcc.Graph(id='total_bases_sequenced-graph'), span=indicator_span),
                    dmc.Col(dcc.Graph(id='q20_score-graph'), span=indicator_span),
                    dmc.Col(dcc.Graph(id='q30_score-graph'), span=indicator_span)
                ]),

                dmc.Grid([
                    dmc.Col(dcc.Graph(id='mean-quality-per-base-plot'), span=12),
                    dmc.Col(dcc.Graph(id='read-length-distribution-plot'), span=12),
                    dmc.Col(dcc.Graph(id='gc-content-distribution-plot'), span=12)
                ])

            ], fluid=True)
        else:
            # If no stats are found, display a message.
            qc_layout = dmc.Text("QC app could not be loaded as no QC statistics were found.", align="center")

        self.app.layout = dmc.Container(qc_layout, fluid=True)

    def get_aggregated_mean_quality_score_plot(self):
        # Aggregate and average mean_quality_score per sample_id
        aggregated_stats = SequencingStatistics.objects.filter(user_id=self.user_id).values('sample_name').annotate(
            average_mean_quality_score=Avg('mean_quality_score'))

        if aggregated_stats:
            # Extract sample IDs and their corresponding aggregated mean quality scores
            sample_ids = [stat['sample_name'] for stat in aggregated_stats]
            average_mean_quality_scores = [stat['average_mean_quality_score'] for stat in aggregated_stats]

            # Create a bar plot
            fig = go.Figure(data=[go.Bar(x=sample_ids, y=average_mean_quality_scores)])
            fig.update_layout(
                title='Aggregated Mean Quality Score per Sample',
                xaxis_title='Sample ID',
                yaxis_title='Aggregated Mean Quality Score',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )

            return fig
        else:
            # Return an empty figure or a message if no data is available
            return go.Figure()

    def get_mean_read_length_plot(self):
        # Fetch mean_read_length and sample_id from SequencingStatistics
        aggregated_stats = SequencingStatistics.objects.filter(user_id=self.user_id).values('sample_name').annotate(
            average_mean_read_length=Avg('mean_read_length'))

        if aggregated_stats:
            # Extract sample IDs and their corresponding aggregated mean read lengths
            sample_ids = [stat['sample_name'] for stat in aggregated_stats]
            average_mean_read_lengths = [stat['average_mean_read_length'] for stat in aggregated_stats]

            # Create a bar plot
            fig = go.Figure(data=[go.Bar(x=sample_ids, y=average_mean_read_lengths)])
            fig.update_layout(
                title='Aggregated Mean Read Length per Sample',
                xaxis_title='Sample ID',
                yaxis_title='Aggregated Mean Read Length',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )

            return fig
        else:
            # Return an empty figure or a message if no data is available
            return go.Figure()

    def get_mean_gc_per_sample_plot(self):
        # Fetch mean_read_length and sample_id from SequencingStatistics
        aggregated_stats = SequencingStatistics.objects.filter(user_id=self.user_id).values('sample_name').annotate(
            average_mean_gc_content=Avg('mean_gc_content'))

        if aggregated_stats:
            # Extract sample IDs and their corresponding aggregated mean read lengths
            sample_ids = [stat['sample_name'] for stat in aggregated_stats]
            average_mean_read_lengths = [stat['average_mean_gc_content'] for stat in aggregated_stats]

            # Create a bar plot
            fig = go.Figure(data=[go.Bar(x=sample_ids, y=average_mean_read_lengths)])
            fig.update_layout(
                title='Aggregated Mean GC Content per Sample',
                xaxis_title='Sample ID',
                yaxis_title='Aggregated Mean GC',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )

            return fig
        else:
            # Return an empty figure or a message if no data is available
            return go.Figure()

    def get_total_bases_sequenced_plot(self):
        # Fetch sample_id and total_bases_sequenced from SequencingStatistics
        stats = SequencingStatistics.objects.filter(user_id=self.user_id).values('sample_name', 'total_bases_sequenced')

        if stats:
            # Extract sample IDs and their corresponding total bases sequenced
            sample_ids = [stat['sample_name'] for stat in stats]
            total_bases_sequenced = [stat['total_bases_sequenced'] for stat in stats]

            # Create a bar plot
            fig = go.Figure(data=[go.Bar(x=sample_ids, y=total_bases_sequenced)])
            fig.update_layout(
                title='Total Bases Sequenced per Sample',
                xaxis_title='Sample ID',
                yaxis_title='Total Bases Sequenced',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )

            return fig
        else:
            # Return an empty figure or a message if no data is available
            return go.Figure()
