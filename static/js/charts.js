/**
 * EMS Portal - Chart.js Data Visualizations
 */
document.addEventListener('DOMContentLoaded', function () {
    if (!window.emsChartData) return;
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js is not loaded. Skipping chart initialization.');
        return;
    }

    const chartData = window.emsChartData;

    // SaaS Palette Colors
    const palette = [
        '#2563eb', // Blue
        '#8b5cf6', // Purple
        '#10b981', // Emerald
        '#f59e0b', // Amber
        '#06b6d4', // Cyan
        '#ec4899', // Pink
        '#64748b'  // Slate
    ];

    // 1. Department Distribution Doughnut Chart
    const deptCtx = document.getElementById('deptDistributionChart');
    if (deptCtx && chartData.dept_labels && chartData.dept_labels.length > 0) {
        new Chart(deptCtx, {
            type: 'doughnut',
            data: {
                labels: chartData.dept_labels,
                datasets: [{
                    data: chartData.dept_counts,
                    backgroundColor: palette.slice(0, chartData.dept_labels.length),
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 12,
                            padding: 14,
                            font: {
                                family: "'Plus Jakarta Sans', sans-serif",
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const val = context.raw;
                                const pct = ((val / total) * 100).toFixed(1);
                                return ` ${context.label}: ${val} staff (${pct}%)`;
                            }
                        }
                    }
                },
                cutout: '68%'
            }
        });
    }

    // 2. Monthly Joining Trends Line Chart
    const trendsCtx = document.getElementById('joiningTrendsChart');
    if (trendsCtx && chartData.trend_labels && chartData.trend_labels.length > 0) {
        new Chart(trendsCtx, {
            type: 'line',
            data: {
                labels: chartData.trend_labels,
                datasets: [{
                    label: 'New Joiners',
                    data: chartData.trend_counts,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.08)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: '#2563eb',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return ` Joined: ${context.raw} employee(s)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                family: "'Plus Jakarta Sans', sans-serif",
                                size: 11
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0,
                            font: {
                                family: "'Plus Jakarta Sans', sans-serif",
                                size: 11
                            }
                        },
                        grid: {
                            color: '#f1f5f9'
                        }
                    }
                }
            }
        });
    }
});
