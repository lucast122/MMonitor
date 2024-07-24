import json
import random

import dash_core_components as dcc
import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objs as go
from django_plotly_dash import DjangoDash

from users.models import SequencingStatistics


class QC:
    def __init__(self, user_id):
        self.user_id = user_id
        self.app = DjangoDash('qc', add_bootstrap_links=True)
        self._init_layout()

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

        samples_read_lengths = self.stats_df[['sample_name', 'read_lengths', 'project_id']]

        # Initialize dictionaries to hold aggregated read lengths data
        read_lengths_data = {}
        project_colors = {}
        project_legend_added = {}  # Track which project_id has been added to the legend for name adjustments

        sample_size = 1000  # Target number of read lengths to sample for each plot

        # Process and aggregate read lengths data efficiently
        for _, sample in samples_read_lengths.iterrows():
            sample_name = sample['sample_name']
            project_id = sample['project_id']
            try:
                # Convert string representation of list to actual list and convert each item to int
                read_lengths_list = [int(length) for length in json.loads(sample['read_lengths'])]
            except json.JSONDecodeError:
                continue  # Skip samples with parsing errors

            # Downsample read lengths if there are more than sample_size read lengths
            if len(read_lengths_list) > sample_size:
                read_lengths_list = random.sample(read_lengths_list, sample_size)

            # Aggregate read lengths for the same sample
            if sample_name in read_lengths_data:
                read_lengths_data[sample_name].extend(read_lengths_list)
            else:
                read_lengths_data[sample_name] = read_lengths_list

            # Assign a color for each project_id, but only if it hasn't been assigned yet
            if project_id not in project_colors:
                project_colors[project_id] = self._get_color_for_project_id(project_id)

        # Prepare data for boxplot, ensuring one box per sample_name and adjusting legend for project_id
        boxplot_data = []
        for sample_name, lengths in read_lengths_data.items():
            # Find project_id for the current sample
            project_id = \
            samples_read_lengths.loc[samples_read_lengths['sample_name'] == sample_name, 'project_id'].iloc[0]

            # Determine if this project_id has been added to the legend
            if project_id not in project_legend_added:
                name_for_legend = str(project_id)  # Use project_id for the first sample's legend entry
                project_legend_added[project_id] = True
                showlegend = True
            else:
                name_for_legend = sample_name  # Use sample_name for hover text, but don't add to legend
                showlegend = False  # Don't show in legend to avoid duplicates

            box = go.Box(
                y=lengths,
                boxpoints=False,
                name=name_for_legend,
                legendgroup=str(project_id),  # Use project_id as legendgroup identifier
                marker=dict(color=project_colors[project_id]),
                showlegend=showlegend,
                text=sample_name,  # Use sample_name for hover text
                hoverinfo='text+y',  # Show sample_name and y value on hover
            )
            boxplot_data.append(box)

        # Create a horizontal line trace for the 16S rRNA gene length
        line_trace = go.Scatter(
            x=[0],  # Placeholder x-value
            y=[1550],  # Placeholder y-value for the 16S rRNA gene length
            mode='lines',
            line=dict(color='royalblue', width=2, dash='dot'),
            name='16S rRNA Gene Length',
            showlegend=True
        )

        fig = go.Figure(data=boxplot_data + [line_trace])

        fig.update_layout(
            title='Read Length Distribution per Sample',
            xaxis_title='Sample Name',
            yaxis_title='Read Length',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend_title='Project ID'
        )

        return fig

    def _get_color_for_project_id(self, project_id):
        # You can define a color mapping based on project_id here
        # For simplicity, let's just assign random colors
        return f'rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})'

    def _get_color_for_project_id(self, project_id):
        # You can define a color mapping based on project_id here
        # For simplicity, let's just assign random colors
        return f'rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})'

    def _get_color_for_project_id(self, project_id):
        # You can define a color mapping based on project_id here
        # For simplicity, let's just assign random colors
        return f'rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})'

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
