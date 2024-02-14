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
  
  .horizon-tooltip {
  position: absolute;
  padding: 10px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  border-radius: 4px;
  pointer-events: none; /* Tooltip should not interfere with mouse events */
  z-index: 100;
}

  
    body { margin: 0; }
    .chart-container {
      margin-top: 20px;
    }
    .chart-title {
      text-align: center;
      font-family: sans-serif;
      margin-bottom: 5px;
    }
  
  .horizon-container {
  position: relative;
}

.horizon-container .horizon-tooltip {
  display: none;
  position: absolute;
  max-width: 320px;
  white-space: nowrap;
  padding: 5px;
  border-radius: 3px;
  font: 12px sans-serif;
  color: #eee;
  background: rgba(0,0,0,0.65);
  pointer-events: none;
}

.horizon-container.clickable {
  cursor: pointer;
}
  </style>
  <script src="https://unpkg.com/d3@6"></script>
  <script src="https://unpkg.com/d3-horizon"></script>
</head>
<body>
  <div id="horizon-charts"></div>

  <script>
    const width = window.innerWidth > 1680 ? 1680 : window.innerWidth;
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
                .tooltipContent(({ x, y }) => `<b>${taxon[0]}</b><br><b>${x}</b>: ${Math.abs(Math.round(y * 1e3) / 1e3)} ${y > 0 ? 'increase' : 'decrease'}`)
            .interpolationCurve(d3.curveBasis); // Curve function for interpolation

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
