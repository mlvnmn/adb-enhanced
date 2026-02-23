import { useEffect, useRef } from 'react';

function severityClass(sev) {
    const s = sev?.toLowerCase();
    if (s === 'critical') return 'high';
    return s;
}

export default function ActivityLog({ logs, hasDevice }) {
    const containerRef = useRef(null);

    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <section className="data-grid-section glass-panel">
            <div className="panel-header">
                <div className="panel-title">
                    <i className="fa-solid fa-list-ul text-cyan"></i>
                    <span>Live Forensic Activity Log</span>
                    {logs.length > 0 && (
                        <span className="source-badge">
                            <span className="source-dot"></span>
                            REAL ADB DATA
                        </span>
                    )}
                </div>
                <div className="panel-actions">
                    <span className="log-count mono">{logs.length} entries</span>
                </div>
            </div>
            <div className="table-container" ref={containerRef}>
                {!hasDevice && logs.length === 0 ? (
                    <div className="empty-state">
                        <i className="fa-solid fa-plug-circle-exclamation empty-icon"></i>
                        <span className="empty-title">Waiting for ADB device...</span>
                        <span className="empty-hint">
                            Connect an Android device via USB with <strong>USB Debugging</strong> enabled.
                            <br />Real logcat data will appear here automatically.
                        </span>
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>TIMESTAMP</th>
                                <th>SOURCE</th>
                                <th>ACTIVITY TYPE</th>
                                <th>SEVERITY LEVEL</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.map((log, index) => (
                                <tr key={log.id} className={index === logs.length - 1 ? 'new-row' : ''}>
                                    <td className="mono">{log.timestamp}</td>
                                    <td>{log.appName}</td>
                                    <td>{log.eventType}</td>
                                    <td>
                                        <span className={`severity ${severityClass(log.severity)}`}>
                                            {log.severity}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </section>
    );
}
