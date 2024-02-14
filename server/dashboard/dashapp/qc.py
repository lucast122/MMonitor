import ast
import hashlib

import dash_core_components as dcc
import dash_mantine_components as dmc
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from django_plotly_dash import DjangoDash

from users.models import SequencingStatistics


def string_to_list(string_repr):
    return ast.literal_eval(string_repr)


def subsample(read_lengths):
    # If read_lengths is longer than 200, return a random sample of 200 elements
    if len(read_lengths) > 200:
        return pd.Series(read_lengths).sample(n=200, random_state=42, replace=True).tolist()
    else:
        return read_lengths


class QC:
    def __init__(self, user_id):
        self.user_id = user_id
        self.app = DjangoDash('qc', add_bootstrap_links=True)
        self.colors = [
            '#556b2f', '#6b8e23', '#006400', '#708090',
            '#8b0000', '#3cb371', '#bc8f8f', '#663399', '#008080', '#bdb76b', '#4682b4',
            '#000080', '#9acd32', '#20b2aa', '#cd5c5c', '#32cd32', '#daa520', '#8fbc8f',
            '#8b008b', '#b03060', '#d2b48c', '#ff0000', '#ff8c00', '#ffd700', '#ffff00',
            '#c71585', '#00ff00', '#ba55d3', '#00ff7f', '#4169e1', '#e9967a', '#dc143c',
            '#00ffff', '#00bfff', '#f4a460', '#0000ff', '#a020f0', '#adff2f', '#ff7f50',
            '#ff00ff', '#db7093', '#eee8aa', '#6495ed', '#dda0dd', '#87ceeb', '#ff1493',
            '#f5f5dc', '#afeeee', '#ee82ee', '#98fb98', '#7fffd4', '#e6e6fa', '#ffc0cb'
        ]
        self._init_layout()

        # 55 distinct colors generated using https://mokole.com/palette.html (input: 55, 5% 90%, 1000 loops)

    def get_data(self):
        stats = SequencingStatistics.objects.filter(user_id=self.user_id)
        if not stats.exists():
            return pd.DataFrame(), None  # Return an empty DataFrame and None if no records are found
        return pd.DataFrame.from_records(stats.values()), stats

    def _init_layout(self):
        self.stats_df, self.stats = self.get_data()
        if self.stats:
            self.unique_sample_ids = self.stats.values('sample_name').distinct()
            self.unique_sample_ids = [item['sample_name'] for item in self.unique_sample_ids]
        else:
            self.unique_sample_ids = []

        qc_layout = self._create_qc_layout() if not self.stats_df.empty else self._create_empty_layout()
        self.app.layout = dmc.Container(qc_layout, fluid=True)

    def _create_qc_layout(self):
        indicator_span = 2

        qc_layout = dmc.Container([
            dmc.Title("Quality of all samples", align="center", style={"marginBottom": "20px"}),

            dmc.Grid([
                dmc.Col(dcc.Graph(id='average-read-length-plot', figure=self.get_mean_read_length_plot()), span=12),
                dmc.Col(dcc.Graph(id='read-length-boxplot', figure=self.create_read_length_boxplots()), span=12),
                dmc.Col(dcc.Graph(id='average-read-quality-plot', figure=self.get_aggregated_mean_quality_score_plot()),
                        span=12),
                dmc.Col(dcc.Graph(figure=self.get_mean_gc_per_sample_plot()), span=12),
                dmc.Col(dcc.Graph(id='total-bases-sample-plot', figure=self.get_total_bases_sequenced_plot()), span=12),
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

        return qc_layout

    def _create_empty_layout(self):
        return dmc.Text("QC app could not be loaded as no QC statistics were found.", align="center")

    def create_read_length_boxplots(self):
        if not self.stats.exists():
            return go.Figure()

        # Apply the string_to_list function to convert the strings to lists
        self.stats_df['read_lengths'] = self.stats_df['read_lengths'].apply(string_to_list)

        # Create a list of dictionaries to store flattened data
        flattened_data = []

        # Iterate over rows of the DataFrame and append flattened data
        for _, row in self.stats_df.iterrows():
            sample_name = row['sample_name']
            read_lengths = row['read_lengths']
            project_id = row['project_id']
            flattened_data.extend(
                [{'sample_name': sample_name, 'read_lengths': rl, 'project_id': project_id} for rl in read_lengths])

        # Create the DataFrame from the list of dictionaries
        flattened_data_df = pd.DataFrame(flattened_data)

        # Create the box plot
        fig = px.box(flattened_data_df, x='sample_name', y='read_lengths', color='project_id', points=False,
                     range_y=[0, 4000])
        fig.add_hline(y=1550, line_dash="dot", line_color="grey")

        fig.update_layout(
            title='Read Length Distribution per Sample',
            xaxis_title='Sample Name',
            yaxis_title='Read Length',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend_title='Project ID',
            height=850,

            font=dict(size=20)  # Adjust the font size here
        )

        return fig

    def _get_color_for_project_id(self, project_id):
        """
        Generates a consistent color for a given project_id based on a hash function.
        """
        # Define a palette of colors to cycle through. Add more colors for a larger variety.
        color_palette = self.colors

        # Use a hash function to ensure consistency between runs
        hash_value = int(hashlib.sha256(project_id.encode('utf-8')).hexdigest(), 16)
        color_index = hash_value % len(color_palette)  # Map the hash value to an index in the palette

        return color_palette[color_index]

    def get_aggregated_mean_quality_score_plot(self):
        if not self.stats.exists():
            return go.Figure()

        aggregated_stats = self.stats_df.groupby('sample_name')['mean_quality_score'].mean().reset_index()

        fig = go.Figure(data=[go.Bar(x=aggregated_stats['sample_name'], y=aggregated_stats['mean_quality_score'])])
        fig.update_layout(
            title='Aggregated Mean Quality Score per Sample',
            xaxis_title='Sample ID',
            yaxis_title='Aggregated Mean Quality Score',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        return fig

    def get_mean_read_length_plot(self):
        if not self.stats.exists():
            return go.Figure()

        aggregated_stats = self.stats_df.groupby('sample_name')['mean_read_length'].mean().reset_index()

        fig = go.Figure(data=[go.Bar(x=aggregated_stats['sample_name'], y=aggregated_stats['mean_read_length'])])
        fig.update_layout(
            title='Aggregated Mean Read Length per Sample',
            xaxis_title='Sample ID',
            yaxis_title='Aggregated Mean Read Length',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        return fig

    def get_mean_gc_per_sample_plot(self):
        if not self.stats.exists():
            return go.Figure()

        aggregated_stats = self.stats_df.groupby('sample_name')['mean_gc_content'].mean().reset_index()

        fig = go.Figure(data=[go.Bar(x=aggregated_stats['sample_name'], y=aggregated_stats['mean_gc_content'])])
        fig.update_layout(
            title='Aggregated Mean GC Content per Sample',
            xaxis_title='Sample ID',
            yaxis_title='Aggregated Mean GC',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        return fig

    def get_total_bases_sequenced_plot(self):
        if not self.stats.exists():
            return go.Figure()

        fig = go.Figure(data=[go.Bar(x=self.stats_df['sample_name'], y=self.stats_df['total_bases_sequenced'])])
        fig.update_layout(
            title='Total Bases Sequenced per Sample',
            xaxis_title='Sample ID',
            yaxis_title='Total Bases Sequenced',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )

        return fig
