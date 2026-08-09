// Charts initialization and management for results page
let voteChart = null;

function initializeCharts() {
    // Initialize vote distribution chart
    initVoteDistributionChart();
    
    // Set up real-time updates if needed
    setupChartUpdates();
}

async function initVoteDistributionChart() {
    try {
        // Fetch chart data from API
        const response = await fetch('/api/results');
        const data = await response.json();
        
        const ctx = document.getElementById('voteChart');
        if (!ctx) {
            console.warn('Chart canvas not found');
            return;
        }
        
        // Destroy existing chart if it exists
        if (voteChart) {
            voteChart.destroy();
        }
        
        // Prepare chart data
        const chartData = {
            labels: data.labels,
            datasets: [{
                label: 'Votes',
                data: data.votes,
                backgroundColor: [
                    'rgba(59, 130, 246, 0.8)',   // Blue
                    'rgba(16, 185, 129, 0.8)',   // Green
                    'rgba(239, 68, 68, 0.8)',    // Red
                    'rgba(245, 158, 11, 0.8)',   // Yellow
                    'rgba(139, 92, 246, 0.8)',   // Purple
                    'rgba(236, 72, 153, 0.8)',   // Pink
                    'rgba(34, 197, 94, 0.8)',    // Emerald
                    'rgba(249, 115, 22, 0.8)',   // Orange
                ],
                borderColor: [
                    'rgba(59, 130, 246, 1)',
                    'rgba(16, 185, 129, 1)',
                    'rgba(239, 68, 68, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(139, 92, 246, 1)',
                    'rgba(236, 72, 153, 1)',
                    'rgba(34, 197, 94, 1)',
                    'rgba(249, 115, 22, 1)',
                ],
                borderWidth: 2,
                hoverBorderWidth: 3,
                hoverBorderColor: '#1f2937',
            }]
        };
        
        // Chart configuration
        const config = {
            type: 'doughnut',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            font: {
                                size: 12,
                                family: 'Inter, sans-serif'
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#374151',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} votes (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 1000,
                    easing: 'easeInOutQuart'
                },
                cutout: '50%',
                elements: {
                    arc: {
                        borderWidth: 2
                    }
                }
            }
        };
        
        // Create the chart
        voteChart = new Chart(ctx, config);
        
        // Add click handler for chart segments
        ctx.onclick = function(evt) {
            const points = voteChart.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, true);
            if (points.length) {
                const firstPoint = points[0];
                const label = voteChart.data.labels[firstPoint.index];
                const value = voteChart.data.datasets[firstPoint.datasetIndex].data[firstPoint.index];
                showCandidateDetails(label, value);
            }
        };
        
    } catch (error) {
        console.error('Error initializing vote chart:', error);
        showChartError('Failed to load voting results chart');
    }
}

function setupChartUpdates() {
    // Listen for data updates and refresh chart
    document.addEventListener('dataUpdated', function(event) {
        if (event.detail && event.detail.chartData) {
            updateChart(event.detail.chartData);
        }
    });
}

function updateChart(newData) {
    if (!voteChart) return;
    
    try {
        // Update chart data
        voteChart.data.labels = newData.labels;
        voteChart.data.datasets[0].data = newData.votes;
        
        // Animate the update
        voteChart.update('active');
        
        // Update total votes display
        const totalVotes = newData.votes.reduce((a, b) => a + b, 0);
        const totalVotesElement = document.getElementById('total-votes');
        if (totalVotesElement) {
            animateNumber(totalVotesElement, parseInt(totalVotesElement.textContent), totalVotes);
        }
        
    } catch (error) {
        console.error('Error updating chart:', error);
    }
}

function showCandidateDetails(candidateName, votes) {
    // Create modal or tooltip with candidate details
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-xl shadow-2xl p-8 max-w-md w-full animate-fade-in">
            <div class="text-center">
                <div class="w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i class="fas fa-user text-3xl text-white"></i>
                </div>
                <h2 class="text-2xl font-bold text-gray-900 mb-2">${candidateName}</h2>
                <div class="text-4xl font-bold text-blue-600 mb-2">${votes}</div>
                <div class="text-gray-600 mb-6">Total Votes</div>
                <button onclick="this.closest('.fixed').remove()" 
                        class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    Close
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close on backdrop click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (modal.parentNode) {
            modal.remove();
        }
    }, 5000);
}

function showChartError(message) {
    const chartContainer = document.getElementById('voteChart').parentElement;
    chartContainer.innerHTML = `
        <div class="text-center py-12">
            <i class="fas fa-exclamation-triangle text-4xl text-red-500 mb-4"></i>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Chart Error</h3>
            <p class="text-gray-600">${message}</p>
            <button onclick="location.reload()" 
                    class="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                <i class="fas fa-redo mr-2"></i>Retry
            </button>
        </div>
    `;
}

function animateNumber(element, start, end, duration = 1000) {
    if (start === end) return;
    
    const range = end - start;
    const stepTime = Math.abs(Math.floor(duration / range));
    const timer = setInterval(function() {
        start += (end > start) ? 1 : -1;
        element.textContent = start;
        if (start === end) {
            clearInterval(timer);
        }
    }, stepTime);
}

// Alternative chart types for different views
function createBarChart(data) {
    const ctx = document.getElementById('voteChart');
    if (!ctx) return;
    
    if (voteChart) {
        voteChart.destroy();
    }
    
    voteChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Votes',
                data: data.votes,
                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

function createLineChart(data) {
    const ctx = document.getElementById('voteChart');
    if (!ctx) return;
    
    if (voteChart) {
        voteChart.destroy();
    }
    
    voteChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Vote Progression',
                data: data.votes,
                borderColor: 'rgba(59, 130, 246, 1)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: 'rgba(59, 130, 246, 1)',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Chart type switcher
function switchChartType(type) {
    fetch('/api/results')
        .then(response => response.json())
        .then(data => {
            switch(type) {
                case 'doughnut':
                    initVoteDistributionChart();
                    break;
                case 'bar':
                    createBarChart(data);
                    break;
                case 'line':
                    createLineChart(data);
                    break;
                default:
                    initVoteDistributionChart();
            }
        })
        .catch(error => {
            console.error('Error switching chart type:', error);
        });
}

// Export chart as image
function exportChart() {
    if (!voteChart) return;
    
    const url = voteChart.toBase64Image();
    const link = document.createElement('a');
    link.download = 'voting-results-chart.png';
    link.href = url;
    link.click();
}

// Real-time updates (if WebSocket is implemented later)
function connectWebSocket() {
    // Placeholder for future WebSocket implementation
    // This would enable real-time chart updates without page refresh
}

// Cleanup function
function destroyCharts() {
    if (voteChart) {
        voteChart.destroy();
        voteChart = null;
    }
}

// Handle window resize
window.addEventListener('resize', function() {
    if (voteChart) {
        voteChart.resize();
    }
});

// Handle visibility change (pause updates when tab is not active)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Pause any ongoing animations or updates
        if (voteChart) {
            voteChart.stop();
        }
    } else {
        // Resume updates when tab becomes active
        if (voteChart) {
            voteChart.update();
        }
    }
});
