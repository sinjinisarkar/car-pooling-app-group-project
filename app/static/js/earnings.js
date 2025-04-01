document.addEventListener("DOMContentLoaded", function () {
    // displaying the graph
    const canvas = document.getElementById("earningsChart");
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
                label: 'Weekly Earnings (£)',
                data: data,
                borderWidth: 1,
                backgroundColor: '#e6d6fc'
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

    // Expose animation function globally
    window.animateEarnings = function () {
        const element = document.getElementById("totalEarnings");
        if (!element) return;

        const target = parseFloat(element.dataset.total);
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
            element.textContent = `£${current.toFixed(2)}`;
        }, 1000 / fps);
    };
}); 