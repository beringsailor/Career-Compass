document.addEventListener('DOMContentLoaded', function() {
    updateDashboard(null);

    document.getElementById('categoryDropdown').addEventListener('change', function() {
        const keyword = this.value;
        updateDashboard(keyword);
        document.getElementById('dashboard-heading').textContent = keyword + ' 就業市場情報';
    });
});

function updateDashboard(keyword) {
    document.getElementById('loadingIndicator').style.display = 'block';
    document.getElementById('chartDiv').style.display = 'none';

    Promise.all([
        fetchWordCloud(keyword),
        createPieChart(keyword),
        createRegionBarChart(keyword),
        createJobRatioBarChart(keyword),
        // createCategoryBarChart()
    ]).then(() => {
        document.getElementById('loadingIndicator').style.display = 'none';
        document.getElementById('chartDiv').style.display = 'flex';
    }).catch(error => {
        console.error('Error loading dashboard components:', error);
        document.getElementById('loadingIndicator').style.display = 'none';
    });
}

async function fetchWordCloud(keyword) {
    try {
        const response = await fetch('/api/dashboard/generate_wordcloud', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({'input_text': keyword})
        });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        document.getElementById('wordcloud').src = url;
    } catch (error) {
        console.error('Error fetching word cloud:', error);
    }
}

function createPieChart(keyword) {
    fetch('/api/dashboard/edu_level', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({'input_text': keyword})
    })
    .then(response => response.json())
    .then(data => updatePieChart(data.values, data.labels))
    .catch(error => {
        console.error('Error fetching pie chart data:', error);
    });
}

function updatePieChart(values, labels) {
    const data = [{
        type: "pie",
        values: values,
        labels: labels,
        textinfo: "label+percent",
        textposition: "outside",
        hole: .6,
        automargin: true
    }];
    const layout = {
        height: 350,
        width: 350,
        showlegend: false
    };
    Plotly.newPlot('edu-chart', data, layout);
}

function createRegionBarChart(keyword) {
    fetch('/api/dashboard/region_salary', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({'input_text': keyword})
    })
    .then(response => response.json())
    .then(data => updateRegionBarChart(data.region, data.region_average))
    .catch(error => {
        console.error('Error fetching region bar chart data:', error);
    });
}

function updateRegionBarChart(region, region_average) {
    const data = [{
        type: 'bar',
        x: region_average,
        y: region,
        width: 0.5,
        orientation: 'h'
    }];
    const layout = {
        height: 640,
        width: 400,
        yaxis: {autorange: "reversed"},
        margin: {"t": 80, "b": 80, "l": 80, "r": 80},
        showlegend: false
    };
    Plotly.newPlot('region-chart', data, layout);
}

function createJobRatioBarChart(keyword) {
    fetch('/api/dashboard/job_vacancy', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({'input_text': keyword})
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to fetch job vacancy data');
        return response.json();
    })
    .then(data => updateJobRatioBarChart(keyword, data.chose_cat, data.others, data.dates))
    .catch(error => {
        console.error('Error updating job vacancy ratio chart:', error);
    });
}

function updateJobRatioBarChart(keyword, chose_cat, others, dates) {
    const data1 = {
        type: 'bar',
        name: keyword ? String(keyword) : '所有職缺',
        x: dates,
        y: chose_cat
    };
    const data2 = {
        type: 'bar',
        name: '其他分類職缺',
        x: dates,
        y: others
    };

    var data = [data1, data2];

    const layout = {
        height: 350,
        width: 350,
        barmode: 'stack',
        showlegend: true
    };
    Plotly.newPlot('ratio-chart', data, layout);
}

function createCategoryBarChart() {
    // Assuming no keyword necessary for category bar chart
    fetch('/api/dashboard/job_salary')
    .then(response => response.json())
    .then(data => {
        updateCategoryBarChart(data.categories, data.values)
    })
    .catch(error => {
        console.error('Error fetching category bar chart data:', error);
    });
}

function updateCategoryBarChart(categories, values) {
    const data = [{
        type: "bar",
        x: values,
        y: categories,
        orientation: 'h'
    }];
    const layout = {
        height: 450,
        width: 540,
        yaxis: {autorange: "reversed"},
        margin: {"t": 100, "b": 100, "l": 100, "r": 100},
        showlegend: false
    };
    Plotly.newPlot('category-chart', data, layout);
}
