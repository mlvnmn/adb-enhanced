document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Configuration
    const chartContext = document.getElementById('behaviorChart').getContext('2d');
    const logBody = document.getElementById('logBody');
    const activityLog = document.querySelector('.table-container');

    // 2. Setup Chart.js
    let chartData = {
        labels: Array.from({length: 20}, (_, i) => i),
        datasets: [
            {
                label: 'Behavioral Baseline',
                data: Array.from({length: 20}, () => Math.random() * 40 + 30),
                borderColor: '#475569',
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                tension: 0.4
            },
            {
                label: 'Real-time Usage',
                data: Array.from({length: 20}, () => Math.random() * 50 + 25),
                borderColor: '#00f2ff',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                backgroundColor: 'rgba(0, 242, 255, 0.05)',
                tension: 0.4
            }
        ]
    };

    const behaviorChart = new Chart(chartContext, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#64748b', font: { size: 10 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { display: false }
                }
            },
            animation: { duration: 800 }
        }
    });

    // 3. Simulated Live Log Data
    const appNames = [
        'com.android.chrome', 'com.whatsapp', 'com.instagram.android', 
        'com.google.android.youtube', 'com.google.android.gm', 
        'com.android.settings', 'com.crypto.ledger', 'system_server'
    ];
    
    const eventTypes = [
        'API Call', 'File Access', 'Network Request', 
        'Permission Update', 'Process Fork', 'Socket Open', 'Auth Attempt'
    ];

    const severities = ['LOW', 'MEDIUM', 'CRITICAL'];

    function createLogRow() {
        const now = new Date();
        const timestamp = now.toTimeString().split(' ')[0] + '.' + now.getMilliseconds().toString().padStart(3, '0');
        const app = appNames[Math.floor(Math.random() * appNames.length)];
        const event = eventTypes[Math.floor(Math.random() * eventTypes.length)];
        const severity = severities[Math.floor(Math.random() * severities.length)];
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="mono">${timestamp}</td>
            <td>${app}</td>
            <td>${event}</td>
            <td><span class="severity ${severity.toLowerCase()}">${severity}</span></td>
        `;
        
        return tr;
    }

    // 4. Update Loop
    setInterval(() => {
        // Update Chart
        behaviorChart.data.datasets[1].data.shift();
        const newVal = Math.random() * 60 + 20;
        behaviorChart.data.datasets[1].data.push(newVal);
        behaviorChart.update('none');

        // Add Log Row
        const newRow = createLogRow();
        logBody.appendChild(newRow);
        
        // Keep scroll at bottom
        activityLog.scrollTop = activityLog.scrollHeight;

        // Cleanup log (keep last 50)
        if (logBody.children.length > 50) {
            logBody.removeChild(logBody.children[0]);
        }
    }, 1500);

    // 5. Sidebar Interaction
    document.querySelectorAll('.device-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.device-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });
});
