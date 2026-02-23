import { useEffect, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

const POINTS = 30;

function generateBaseline() {
    return Array.from({ length: POINTS }, () => Math.random() * 30 + 35);
}

export default function BehaviorChart({ logs }) {
    const baselineRef = useRef(generateBaseline());
    const realtimeRef = useRef(Array.from({ length: POINTS }, () => Math.random() * 40 + 25));
    const chartRef = useRef(null);

    useEffect(() => {
        if (logs.length === 0) return;
        const lastLog = logs[logs.length - 1];
        const val = lastLog.severity === 'CRITICAL'
            ? Math.random() * 25 + 75
            : lastLog.severity === 'MEDIUM'
                ? Math.random() * 25 + 45
                : Math.random() * 30 + 15;

        realtimeRef.current = [...realtimeRef.current.slice(1), val];

        if (chartRef.current) {
            chartRef.current.data.datasets[1].data = realtimeRef.current;
            // Update anomaly points
            chartRef.current.data.datasets[2].data = realtimeRef.current.map((v, i) =>
                v > 70 ? v : null
            );
            chartRef.current.update('none');
        }
    }, [logs]);

    const data = {
        labels: Array.from({ length: POINTS }, (_, i) => i),
        datasets: [
            {
                label: 'Golden Baseline',
                data: baselineRef.current,
                borderColor: 'rgba(71, 85, 105, 0.8)',
                borderWidth: 2,
                borderDash: [8, 4],
                pointRadius: 0,
                fill: false,
                tension: 0.4,
            },
            {
                label: 'Real-time Activity',
                data: realtimeRef.current,
                borderColor: '#00f2ff',
                borderWidth: 2.5,
                pointRadius: 0,
                fill: true,
                backgroundColor: (ctx) => {
                    const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
                    gradient.addColorStop(0, 'rgba(0, 242, 255, 0.15)');
                    gradient.addColorStop(1, 'rgba(0, 242, 255, 0.0)');
                    return gradient;
                },
                tension: 0.4,
            },
            {
                label: 'Anomaly Markers',
                data: realtimeRef.current.map((v) => v > 70 ? v : null),
                borderColor: 'transparent',
                pointRadius: 6,
                pointBackgroundColor: '#ef4444',
                pointBorderColor: 'rgba(239, 68, 68, 0.4)',
                pointBorderWidth: 3,
                showLine: false,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
            legend: { display: false },
            tooltip: {
                enabled: true,
                backgroundColor: 'rgba(10, 17, 24, 0.95)',
                borderColor: 'rgba(0, 242, 255, 0.2)',
                borderWidth: 1,
                titleFont: { family: 'JetBrains Mono', size: 11 },
                bodyFont: { family: 'Inter', size: 12 },
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(255, 255, 255, 0.04)' },
                ticks: { color: '#64748b', font: { size: 10, family: 'JetBrains Mono' } },
            },
            x: {
                grid: { display: false },
                ticks: { display: false },
            },
        },
        animation: { duration: 400 },
    };

    return (
        <section className="chart-section glass-panel">
            <div className="panel-header">
                <div className="panel-title">
                    <i className="fa-solid fa-brain text-cyan"></i>
                    <span>Behavioral Analysis Engine</span>
                </div>
                <div className="chart-legend">
                    <span className="legend-item"><span className="dot baseline"></span> Golden Baseline</span>
                    <span className="legend-item"><span className="dot real-time"></span> Real-time Activity</span>
                    <span className="legend-item"><span className="dot anomaly"></span> Anomaly</span>
                </div>
            </div>
            <div className="chart-container">
                <Line ref={chartRef} data={data} options={options} />
            </div>
        </section>
    );
}
