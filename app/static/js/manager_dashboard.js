document.addEventListener("DOMContentLoaded", function () {
    // rides published vs bookec chart
    const ridesChartElement = document.getElementById('ridesChart');
    if (!ridesChartElement) return;

    const published = parseInt(ridesChartElement.dataset.published);
    const booked = parseInt(ridesChartElement.dataset.booked);

    const chart = new Chart(ridesChartElement.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Rides Published', 'Rides Booked'],
            datasets: [{
                data: [published, booked],
                backgroundColor: ['#C8E9E7', '#e6d6fc'],
                borderColor: ['#5BBEB7', '#855bbe'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#1f1d21',
                        font: { family: 'Oxanium' }
                    }
                }
            }
        }
    });

    // platform earnings chart
    const canvas = document.getElementById("platformEarningsChart");
    if (!canvas) return;

    const labels = JSON.parse(canvas.dataset.labels);
    const data = JSON.parse(canvas.dataset.values);
    const dateRanges = JSON.parse(canvas.dataset.dates);

    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Weekly Platform Earnings (£)',
                data: data,
                borderWidth: 1,
                backgroundColor: '#C8E9E7',
                borderColor: '#5BBEB7',
                borderWidth: 2      
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const earnings = `£${ctx.raw.toFixed(2)}`;
                            const dateRange = dateRanges[ctx.dataIndex];
                            return [`${earnings}`, `Week: ${dateRange}`];
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: value => '£' + value.toFixed(2)
                    }
                }
            }
        }
    });

    // number animation for total revenue
    const earningsElement = document.getElementById("totalRevenue");
    if (earningsElement) {
        const target = parseFloat(earningsElement.dataset.total);
        let current = 0;
        const duration = 1000;
        const fps = 60;
        const increment = target / (duration / (1000 / fps));

        const interval = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(interval);
            }
            earningsElement.textContent = `£${current.toFixed(2)}`;
        }, 1000 / fps);
    }
});