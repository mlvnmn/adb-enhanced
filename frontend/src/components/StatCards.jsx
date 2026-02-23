import { useState, useEffect } from 'react';

export default function StatCards({ logs, connected, hasDevice, socket }) {
    const [stats, setStats] = useState({
        totalLogs: 0,
        activeProcesses: 0,
        threatLevel: 'LOW',
        alertCount: 0,
    });

    // Try fetching stats from backend
    useEffect(() => {
        if (!connected) return;
        const fetchStats = () => {
            fetch('http://localhost:5000/api/stats')
                .then(r => r.json())
                .then(data => setStats(prev => ({ ...prev, ...data })))
                .catch(() => { });
        };
        fetchStats();
        const interval = setInterval(fetchStats, 5000);
        return () => clearInterval(interval);
    }, [connected]);

    // Listen for live stat updates
    useEffect(() => {
        if (!socket) return;
        const handler = (data) => setStats(prev => ({ ...prev, ...data }));
        socket.on('stats_update', handler);
        return () => socket.off('stats_update', handler);
    }, [socket]);

    // Also compute from local logs as fallback
    useEffect(() => {
        if (logs.length > 0) {
            const critCount = logs.filter(l => l.severity === 'CRITICAL').length;
            const ratio = critCount / logs.length;
            let level = 'LOW';
            if (ratio > 0.4) level = 'CRITICAL';
            else if (ratio > 0.25) level = 'HIGH';
            else if (ratio > 0.1) level = 'ELEVATED';

            setStats(prev => ({
                ...prev,
                totalLogs: Math.max(prev.totalLogs, logs.length),
                threatLevel: prev.threatLevel === 'LOW' ? level : prev.threatLevel,
            }));
        }
    }, [logs]);

    const threatColors = {
        LOW: { bg: 'rgba(16, 185, 129, 0.12)', color: '#10b981', glow: '0 0 20px rgba(16, 185, 129, 0.3)' },
        ELEVATED: { bg: 'rgba(245, 158, 11, 0.12)', color: '#f59e0b', glow: '0 0 20px rgba(245, 158, 11, 0.3)' },
        HIGH: { bg: 'rgba(249, 115, 22, 0.12)', color: '#f97316', glow: '0 0 20px rgba(249, 115, 22, 0.3)' },
        CRITICAL: { bg: 'rgba(239, 68, 68, 0.12)', color: '#ef4444', glow: '0 0 20px rgba(239, 68, 68, 0.3)' },
    };

    const threat = threatColors[stats.threatLevel] || threatColors.LOW;

    const cards = [
        {
            icon: 'fa-solid fa-database',
            label: 'Total Logs Captured',
            value: stats.totalLogs.toLocaleString(),
            accent: 'var(--accent-cyan)',
            accentBg: 'rgba(0, 242, 255, 0.08)',
            accentGlow: 'var(--glow-cyan)',
        },
        {
            icon: 'fa-solid fa-microchip',
            label: 'Active Processes',
            value: stats.activeProcesses || '—',
            accent: 'var(--accent-blue)',
            accentBg: 'rgba(30, 136, 229, 0.08)',
            accentGlow: '0 0 20px rgba(30, 136, 229, 0.3)',
        },
        {
            icon: 'fa-solid fa-shield-virus',
            label: 'Threat Level',
            value: stats.threatLevel,
            accent: threat.color,
            accentBg: threat.bg,
            accentGlow: threat.glow,
            isThreat: true,
        },
    ];

    return (
        <div className="stat-cards-row">
            {cards.map((card, i) => (
                <div
                    className="stat-card glass-panel"
                    key={i}
                    style={{ '--card-accent': card.accent, '--card-accent-bg': card.accentBg }}
                >
                    <div className="stat-card-icon" style={{ color: card.accent, boxShadow: card.accentGlow }}>
                        <i className={card.icon}></i>
                    </div>
                    <div className="stat-card-body">
                        <span className="stat-card-label">{card.label}</span>
                        <span
                            className={`stat-card-value ${card.isThreat ? 'threat-value' : ''}`}
                            style={card.isThreat ? { color: card.accent } : {}}
                        >
                            {card.value}
                        </span>
                    </div>
                    <div className="stat-card-accent-bar" style={{ background: card.accent }}></div>
                </div>
            ))}
        </div>
    );
}
