import { useState, useEffect } from 'react';

export default function AnomalyPanel({ anomalies = [] }) {
    const [expanded, setExpanded] = useState(true);
    const [all, setAll] = useState([]);

    // Load existing anomalies from API on mount
    useEffect(() => {
        fetch('http://localhost:5000/api/anomalies')
            .then(r => r.json())
            .then(data => {
                const mapped = (Array.isArray(data) ? data : []).map(a => ({
                    id: a.id,
                    type: a.alert_type,
                    severity: a.severity || 'HIGH',
                    description: a.description,
                    package: '',
                    category: '',
                    timestamp: a.created_at ? new Date(a.created_at).toLocaleTimeString() : '',
                }));
                setAll(mapped);
            })
            .catch(() => { });
    }, []);

    // Merge new WebSocket anomalies with loaded ones
    useEffect(() => {
        if (anomalies.length > 0) {
            setAll(prev => {
                const ids = new Set(prev.map(a => a.id));
                const newOnes = anomalies.filter(a => !ids.has(a.id));
                return [...newOnes, ...prev].slice(0, 30);
            });
        }
    }, [anomalies]);

    const severityIcon = (sev) => {
        switch (sev) {
            case 'CRITICAL': return 'fa-skull-crossbones';
            case 'HIGH': return 'fa-triangle-exclamation';
            case 'MEDIUM': return 'fa-exclamation-circle';
            default: return 'fa-info-circle';
        }
    };

    const severityClass = (sev) => {
        switch (sev) {
            case 'CRITICAL': return 'anomaly-critical';
            case 'HIGH': return 'anomaly-high';
            case 'MEDIUM': return 'anomaly-medium';
            default: return 'anomaly-low';
        }
    };

    return (
        <section className="anomaly-panel glass-panel">
            <div className="panel-header">
                <div className="panel-title">
                    <i className="fa-solid fa-shield-virus text-cyan"></i>
                    <span>Anomaly Detection Engine</span>
                    {all.length > 0 && (
                        <span className="anomaly-count-badge">{all.length}</span>
                    )}
                </div>
                <button className="btn-outline" onClick={() => setExpanded(!expanded)}>
                    <i className={`fa-solid ${expanded ? 'fa-chevron-up' : 'fa-chevron-down'}`}></i>
                </button>
            </div>

            {expanded && (
                <div className="anomaly-list">
                    {all.length === 0 ? (
                        <div className="anomaly-empty">
                            <i className="fa-solid fa-shield-check"></i>
                            <span>No anomalies detected — System nominal</span>
                        </div>
                    ) : (
                        all.map((a, i) => (
                            <div
                                key={a.id || i}
                                className={`anomaly-item ${severityClass(a.severity)}`}
                            >
                                <div className="anomaly-icon-col">
                                    <i className={`fa-solid ${severityIcon(a.severity)}`}></i>
                                </div>
                                <div className="anomaly-body">
                                    <div className="anomaly-header-row">
                                        <span className="anomaly-type">{a.type}</span>
                                        <span className={`severity ${a.severity?.toLowerCase()}`}>{a.severity}</span>
                                    </div>
                                    <p className="anomaly-desc">{a.description}</p>
                                    <div className="anomaly-meta">
                                        {a.package && <span className="mono">{a.package}</span>}
                                        {a.timestamp && <span>{a.timestamp}</span>}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </section>
    );
}
