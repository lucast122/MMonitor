from django_plotly_dash import DjangoDash
from users.models import SequencingStatistics
import pandas as pd
import dash_core_components as dcc
from dash import html
class QC:

    def get_data(self):
        stats = SequencingStatistics.objects.filter(user_id=self.user_id)

        if not stats.exists():
            return pd.DataFrame(), None  # Return an empty DataFrame and None if no records are found
        return pd.DataFrame.from_records(stats.values()), stats

    def __init__(self, user_id):
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
        num_plots = 7

        if not self.stats_df.empty:
            qc_layout = html.Div([
                dcc.Dropdown(
                    id='sample-dropdown-qc',
                    options=[{'label': name, 'value': name} for name in self.unique_sample_ids],
                    value=self.unique_sample_ids[0] if self.unique_sample_ids else None  # default to the first sample
                ),
                # Container for the two smaller plots
                html.Div([

                    dcc.Graph(id='mean_read_length-graph', style={'width': f"{100/num_plots}%", 'display': 'inline-block'}),
                    dcc.Graph(id='mean_quality_score-graph', style={'width': f"{100/num_plots}%", 'display': 'inline-block'}),
                    dcc.Graph(id='number_of_reads-graph', style={'width': f"{100/num_plots}%", 'display': 'inline-block'}),
                    dcc.Graph(id='total_bases_sequenced-graph', style={'width': f"{100/num_plots}%", 'display': 'inline-block'}),
                    dcc.Graph(id='q20_score-graph', style={'width': f"{100/num_plots}%", 'display': 'inline-block'}),
                    dcc.Graph(id='q30_score-graph', style={'width': f"{100/num_plots}%", 'display': 'inline-block'}),
                    dcc.Graph(id='mean-gc-indicator-plot', style={'width': f"{100/num_plots}%", 'display': 'inline-block'}),


                ], style={'display': 'flex', 'justifyContent': 'center'}),

                dcc.Graph(id='mean-quality-per-base-plot'),
                dcc.Graph(id='read-length-distribution-plot'),
                dcc.Graph(id='gc-content-distribution-plot')

                # Additional plots as needed...
            ])

        else:
            # If no stats are found, display a message.
            qc_layout = html.Div([
                html.H3("QC app could not be loaded as no QC statistics were found.")
            ])

        self.app.layout = qc_layout
