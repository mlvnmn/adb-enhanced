import { useState, useEffect } from 'react';

export default function TopNav({ connected, hasDevice, socket }) {
    const [alertCount, setAlertCount] = useState(0);

    useEffect(() => {
        if (!connected) return;
        fetch('http://localhost:5000/api/alerts')
            .then(r => r.json())
            .then(data => {
                const unresolved = data.filter(a => !a.resolved).length;
                setAlertCount(unresolved);
            })
            .catch(() => { });
    }, [connected]);

    useEffect(() => {
        if (!socket) return;
        const handler = (data) => {
            if (data.alert_count !== undefined) setAlertCount(data.alert_count);
        };
        socket.on('stats_update', handler);
        return () => socket.off('stats_update', handler);
    }, [socket]);

    const statusLabel = !connected ? 'OFFLINE' : hasDevice ? 'LIVE — ADB' : 'WAITING';
    const statusClass = !connected ? 'disconnected' : hasDevice ? 'connected' : 'waiting';

    return (
        <header className="top-nav">
            <div className="nav-left">
                <h1 className="page-title">Enhanced ADB Forensic Monitor</h1>
                <span className="system-status">SYSTEM SECURE // ENCRYPTION AES-256</span>
            </div>
            <div className="nav-right">
                <div className={`ws-status ${statusClass}`}>
                    <span className="ws-dot"></span>
                    {statusLabel}
                </div>
                <div className="search-box">
                    <i className="fa-solid fa-search" style={{ color: 'var(--text-dim)' }}></i>
                    <input type="text" placeholder="Search activities..." />
                </div>
                <div className="alert-bell-container" title="Critical Anomaly Alerts">
                    <i className={`fa-solid fa-bell alert-bell ${alertCount > 0 ? 'active' : ''}`}></i>
                    {alertCount > 0 && (
                        <span className="alert-count-badge">{alertCount > 99 ? '99+' : alertCount}</span>
                    )}
                    <span className="alert-label">CRITICAL ALERT</span>
                </div>
                <div className="avatar">MJ</div>
            </div>
        </header>
    );
}
