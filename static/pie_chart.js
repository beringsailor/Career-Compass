function createPieChart(values, labels) {
  if (!values || !labels) {
      // Make API call to fetch default values and labels
      fetch('/default-data')
          .then(response => response.json())
          .then(data => {
              // Call createPieChart with fetched values and labels
              updatePieChart(data.values, data.labels);
          })
          .catch(error => console.error('Error fetching default data:', error));
  } else {
      // Call updatePieChart with provided values and labels
      updatePieChart(values, labels);
  }
}

function updatePieChart(values, labels) {
  var data = [{
      type: "pie",
      values: values,
      labels: labels,
      textinfo: "label+percent",
      textposition: "outside",
      automargin: true
  }];

  var layout = {
      height: 400,
      width: 400,
      margin: {"t": 0, "b": 0, "l": 0, "r": 0},
      showlegend: false
  };

  // Update the pie chart
  Plotly.newPlot('pie-chart', data, layout);
}

function displaySelectedRegion(clickData) {
  // Assuming 'cursor' is defined and connected to a database

  // Execute SQL query
  var eduTypes = cursor.execute(`
      SELECT LEFT(edu_level, 2) AS min_edu_level, COUNT(*) AS count
      FROM aws_pp.job
      GROUP BY min_edu_level;
  `);

  // Fetch results
  eduTypes = cursor.fetchall();

  var eduName = [];
  var eduNameNum = [];

  // Extract data
  eduTypes.forEach(function(eduType) {
      eduName.push(eduType['min_edu_level']);
      eduNameNum.push(eduType['count']);
  });

  var labels = eduName;
  var values = eduNameNum;

  // Assuming 'go' is defined and available for use
  var fig = go.Figure(data=[go.Pie(labels=labels, values=values)]);
  return fig;
}
