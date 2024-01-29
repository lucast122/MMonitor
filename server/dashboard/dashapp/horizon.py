import dash_html_components as html
from dash_extensions.enrich import html
# from mmonitor.dashapp.app import app
# from mmonitor.dashapp.base_app import BaseApp
# from mmonitor.database.mmonitor_db import MMonitorDBInterface
from django_plotly_dash import DjangoDash


class Horizon:
    """
    App to display the taxonomy abundances in a horizon plot
    """

    def __init__(self, user_id):
        self.app = DjangoDash('horizon')
        self._init_layout()

    def _init_layout(self):
        # Debug: Log the session ID and retrieved data

        test = "if this works then I can add data to the horizon plot!"
        '''
        self.app.layout = html.Div([
            
            html.Iframe(
                # enable all sandbox features
                # see https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe
                # this prevents javascript from running inside the iframe
                # and other things security reasons
                sandbox='allow-scripts allow-forms allow-modals allow-pointer-lock allow-popups allow-presentation allow-same-origin allow-storage-access-by-user-activation',
                srcDoc="""
<!DOCTYPE html>
<meta charset="utf-8">
<style>
  .horizon {
    border-top: solid 1px #000;
    border-bottom: solid 1px #000;
    overflow: hidden;
    position: relative;
  }

  .horizon + .horizon {
    border-top: none;
  }

  .horizon canvas {
    display: block;
    image-rendering: pixelated;
  }

  .horizon .title,
  .horizon .value {
      bottom: 0;
      line-height: 30px;
      margin: 0 6px;
      position: absolute;
      font-family: sans-serif;
      text-shadow: 0 1px 0 rgba(255,255,255,.5);
      white-space: nowrap;
  }

  .horizon .title {
      left: 0;
  }

  .horizon .value {
      right: 0;
  }

</style>

<body>




<script src="https://d3js.org/d3.v4.js"></script>
<script src="https://unpkg.com/d3-horizon-chart@0.0.6"></script>

<script type="text/javascript">

let userId = '{{ user_id }}';
fetch(`/api/chart-data/?user_id=${userId}`)
    .then(response => response.json())
    .then(data => {
        let filteredData = data.filter(d => d.fields && d.fields.taxonomy === "Escherichia coli");
        let rawCounts = filteredData.map(d => d.fields.count);

        // Calculating the changes in counts
        let changesInCounts = rawCounts.map((current, index) => {
            if (index === 0) {
                return current; // First element: change from 0 to its value
            } else {
                return current - rawCounts[index - 1]; // Subsequent elements: change from the previous value
            }
        });
        console.log(changesInCounts);

        // Process changesInCounts for horizon chart
        var horizonChart = d3.horizonChart()
            .height(100)
            .title('Horizon, 1-band')
    .colors(['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#fdae61', '#f46d43', '#d73027']);

        var horizons = d3.select('body').selectAll('.horizon')
            .data([changesInCounts])
            .enter().append('div')
            .attr('class', 'horizon')
            .each(horizonChart);
    })
    .catch(error => {
        console.error('Error fetching data:', error);
    });






</script>""",style={"height": 500, "width": 500},

            )
        ])

    def _init_callbacks(self):
        return
'''

        #         try out other version of the chart

        self.app.layout = html.Div([

            html.Iframe(
                # enable all sandbox features
                # see https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe
                # this prevents javascript from running inside the iframe
                # and other things security reasons
                sandbox='allow-scripts allow-forms allow-modals allow-pointer-lock allow-popups allow-presentation allow-same-origin allow-storage-access-by-user-activation',
                srcDoc="""
<!DOCTYPE html>
<html>
<head>
  <style>
    body { margin: 0; }
    .chart-container {
      margin-top: 20px;
    }
    .chart-title {
      text-align: center;
      font-family: sans-serif;
      margin-bottom: 5px;
    }
  </style>
  <script src="https://unpkg.com/d3@6"></script>
  <script src="https://unpkg.com/d3-horizon"></script>
</head>
<body>
  <div id="horizon-charts"></div>

  <script>
    const width = window.innerWidth > 1920 ? 1920 : window.innerWidth;
    const height = Math.round(width / 64); // Maintain aspect ratio

    let userId = '{{ user_id }}';

    fetch(`/api/chart-data/?user_id=${userId}`)
    .then(response => response.json())
    .then(data => {
        // Group data by taxonomy and calculate total counts
        let taxaCounts = data.reduce((acc, d) => {
            if (d.fields && d.fields.taxonomy) {
                acc[d.fields.taxonomy] = (acc[d.fields.taxonomy] || 0) + d.fields.count;
            }
            return acc;
        }, {});

        // Sort taxa by counts and select top 10
        let topTaxa = Object.entries(taxaCounts)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 20);

        topTaxa.forEach((taxon, idx) => {
            // Filter data for this taxon
            let filteredData = data.filter(d => d.fields && d.fields.taxonomy === taxon[0]);
            let rawCounts = filteredData.map(d => d.fields.count);

            // Calculating the changes in counts
            let changesInCounts = rawCounts.map((current, index) => {
                return index === 0 ? current : current - rawCounts[index - 1];
            });

            // Format the data
            let formattedData = changesInCounts.map((count, index) => [index, count]);

            // Create a container for each horizon plot
            let chartContainer = d3.select("#horizon-charts").append("div")
                                    .attr("class", "chart-container")
                                    .attr("id", `horizon-chart-${idx}`);

            // Add taxon name as a title
            chartContainer.append("div")
                .attr("class", "chart-title")
                .text(taxon[0]);

            // Create horizon plot
            d3.horizon()(chartContainer.node())
                .width(width)
                .height(height)
                .bands(4)
                .mode('mirror')
                .data(formattedData)
                .duration(4000)
                .tooltipContent(({ x, y }) => `<b>${taxon[0]}</b><br><b>${x}</b>: ${Math.abs(Math.round(y * 1e3) / 1e3)} ${y > 0 ? 'increase' : 'decrease'}`);
        });
    });
  </script>
</body>
</html>
""", style={"height": (1920 / 32) * 20, "width": 1920},

            )
        ])

    def _init_callbacks(self):
        return
