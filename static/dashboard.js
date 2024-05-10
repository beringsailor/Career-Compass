// load inital js content
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts when the DOM is loaded
    fetchWordCloud(null);
    createPieChart(null);
    createRegionBarChart(null);
    createCategoryBarChart();
    createJobRatioBarChart(null);

    // Add event listeners to all buttons
    document.getElementById('categoryDropdown').addEventListener('change', function() {
        const keyword = this.value;
        fetchWordCloud(keyword);
        createPieChart(keyword);
        createRegionBarChart(keyword);
        createJobRatioBarChart(keyword);

        // Update the heading text with the selected value
        document.getElementById('dashboard-heading').textContent = keyword + ' 就業市場情報';
    });
});

// wordcloud
async function fetchWordCloud(keyword) {
    try {
        const response = await fetch('/api/dashboard/generate_wordcloud', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 'input_text': keyword })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const img = document.getElementById('wordcloud');
        await new Promise(resolve => {
            img.onload = resolve;
            img.src = url;
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// pie-chart
function createPieChart(keyword) {
    fetch('/api/dashboard/edu_level', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }, 
        body: JSON.stringify({ 'input_text': keyword })
    })
    .then(response => response.json())
    .then(data => {
        updatePieChart(data.values, data.labels);
    })
    .catch(error => console.error('Error fetching data:', error));
}

function updatePieChart(values, labels) {
    var data = [{
        type: "pie",
        values: values,
        labels: labels,
        textinfo: "label+percent",
        textposition: "outside",
        hole: .6,
        automargin: true
    }];

    var layout = {
        height: 350,
        width: 350,
        showlegend: false
    };

    // Update the pie chart
    Plotly.newPlot('edu-chart', data, layout);
}

// barchart for region
function createRegionBarChart(keyword) {
    fetch('/api/dashboard/region_salary', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }, 
        body: JSON.stringify({ 'input_text': keyword })
    })
    .then(response => response.json())
    .then(data => {
        updateRegionBarChart(data.region, data.region_average);
    })
    .catch(error => console.error('Error:', error));
}

function updateRegionBarChart(region, region_avg) {
    const data = [{
        type: 'bar',
        x: region_avg,
        y: region,
        width: 0.5,
        // text: region,
        orientation: 'h'
    }];

    const layout = {
        height: 640,
        width: 400,
        yaxis: {autorange: "reversed"},
        margin: {"t": 80, "b": 80, "l": 80, "r": 80},
        showlegend: false
    };

    Plotly.newPlot('region-chart', data, layout)
}

// barchart for job vacancy ratio
function createJobRatioBarChart(keyword) {
    fetch('/api/dashboard/job_vacancy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }, 
        body: JSON.stringify({ 'input_text': keyword })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log('Response from /api/dashboard/job_vacancy:', data);
        updateJobRatioBarChart(keyword, data.chose_cat, data.others, data.dates);
    })
    .catch(error => console.error('Error:', error));
}

function updateJobRatioBarChart(keyword, chose_cat, others, dates) {
    const data1 = {
        type: 'bar',
        name: keyword ? String(keyword) : '所有職缺',
        x: dates,
        y: chose_cat,
    };

    const data2 = {
        type: 'bar',
        name: '其他分類職缺',
        x: dates,
        y: others,
    };

    var data = [data1, data2];

    const layout = {
        height: 350,
        width: 350,
        barmode: 'stack',
        showlegend: true
    };

    Plotly.newPlot('ratio-chart', data, layout)
}

// barchart for job_category
function createCategoryBarChart() {
    fetch('/api/dashboard/job_salary')
        .then(response => response.json())
        .then(data => {
            console.log('Received JSON data:', data);
            updateCategoryBarChart(data.category, data.category_average);
        })
        .catch(error => console.error('Error:', error));
}

function updateCategoryBarChart(category, category_avg) {
    const data = [{
        type: "bar",
        x: category_avg,
        y: category,
        orientation: 'h'
    }];

    const layout = {
        height: 450,
        width: 540,
        yaxis: {autorange: "reversed"},
        margin: {"t": 100, "b": 100, "l": 100, "r": 100},
        showlegend: false
    };

    Plotly.newPlot('category-chart', data, layout)
}