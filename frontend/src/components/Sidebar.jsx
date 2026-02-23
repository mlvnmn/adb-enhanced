import { useState, useEffect } from 'react';

export default function Sidebar({ socket }) {
    const [devices, setDevices] = useState([]);
    const [activeDevice, setActiveDevice] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://localhost:5000/api/devices')
            .then((res) => res.json())
            .then((data) => {
                setDevices(data);
                if (data.length > 0) setActiveDevice(data[0].id);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (!socket) return;
        const handler = (data) => setDevices(data);
        socket.on('devices_update', handler);
        return () => socket.off('devices_update', handler);
    }, [socket]);

    const onlineCount = devices.filter((d) => d.status === 'online').length;

    const getConnectionType = (serial) => {
        if (!serial) return 'usb';
        const s = serial.toLowerCase();
        if (s.includes('wifi') || s.includes(':5555') || s.includes('.')) return 'wifi';
        return 'usb';
    };

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <i className="fa-solid fa-shield-halved logo-icon"></i>
                <div>
                    <span className="brand-text">ADB MONITOR</span>
                    <span className="brand-sub">FORENSIC EDITION</span>
                </div>
            </div>

            <div className="section-label">CONNECTED DEVICES</div>

            <ul className="device-list">
                {loading ? (
                    <li className="device-item" style={{ justifyContent: 'center', color: 'var(--text-dim)' }}>
                        <i className="fa-solid fa-spinner fa-spin"></i>
                        <span style={{ marginLeft: 8 }}>Scanning ADB...</span>
                    </li>
                ) : devices.length === 0 ? (
                    <li className="device-item device-empty">
                        <i className="fa-solid fa-plug-circle-xmark"></i>
                        <span>No devices connected</span>
                        <span className="device-hint">Connect via USB or WiFi ADB</span>
                    </li>
                ) : (
                    devices.map((device) => {
                        const connType = getConnectionType(device.serial);
                        return (
                            <li
                                key={device.id}
                                className={`device-item ${device.id === activeDevice ? 'active' : ''}`}
                                onClick={() => setActiveDevice(device.id)}
                            >
                                <div className="device-info">
                                    <span className="device-name">{device.model}</span>
                                    <span className="device-id">{device.serial}</span>
                                    <div className="device-meta">
                                        <span className={`conn-badge conn-${connType}`}>
                                            <i className={`fa-solid ${connType === 'wifi' ? 'fa-wifi' : 'fa-usb'}`}></i>
                                            {connType.toUpperCase()}
                                        </span>
                                        {device.os_version && (
                                            <span className="os-badge">{device.os_version}</span>
                                        )}
                                    </div>
                                </div>
                                <span className={`status-dot ${device.status === 'online' ? 'online' : 'offline'}`}></span>
                            </li>
                        );
                    })
                )}
            </ul>

            <div className="sidebar-footer">
                <div className="connection-stats">
                    <span>Signals: {onlineCount} Active</span>
                    <i className="fa-solid fa-wifi text-cyan"></i>
                </div>
            </div>
        </aside>
    );
}
