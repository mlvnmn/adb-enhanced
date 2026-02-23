import { useEffect, useState, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';

const BACKEND_URL = 'http://localhost:5000';

export function useSocket() {
    const [connected, setConnected] = useState(false);
    const [hasDevice, setHasDevice] = useState(false);
    const [logs, setLogs] = useState([]);
    const [anomalies, setAnomalies] = useState([]);
    const [foreground, setForeground] = useState(null);
    const socketRef = useRef(null);
    const MAX_LOGS = 80;
    const MAX_ANOMALIES = 30;

    const addLog = useCallback((entry) => {
        setLogs((prev) => {
            const next = [...prev, entry];
            return next.length > MAX_LOGS ? next.slice(next.length - MAX_LOGS) : next;
        });
    }, []);

    const addAnomaly = useCallback((entry) => {
        setAnomalies((prev) => {
            const next = [entry, ...prev];
            return next.length > MAX_ANOMALIES ? next.slice(0, MAX_ANOMALIES) : next;
        });
    }, []);

    useEffect(() => {
        const socket = io(BACKEND_URL, {
            transports: ['websocket'],
            reconnectionAttempts: 5,
            timeout: 5000,
        });

        socketRef.current = socket;

        socket.on('connect', () => setConnected(true));

        socket.on('status', (data) => {
            setHasDevice(data.mode === 'live');
        });

        socket.on('new_log', (data) => {
            setHasDevice(true);
            const localTs = new Date(data.timestamp).toLocaleTimeString('en-IN', {
                hour: '2-digit', minute: '2-digit', second: '2-digit',
                hour12: false, fractionalSecondDigits: 3,
            });
            addLog({
                id: data.id || Date.now() + Math.random(),
                timestamp: localTs,
                appName: data.app_name,
                eventType: data.event_type,
                severity: data.severity,
                source: data.source || 'unknown',
            });
        });

        socket.on('anomaly_detected', (data) => {
            addAnomaly({
                id: data.id || Date.now(),
                type: data.type,
                severity: data.severity,
                description: data.description,
                package: data.package,
                category: data.category,
                timestamp: data.timestamp,
            });
        });

        socket.on('foreground_update', (data) => {
            setForeground(data);
        });

        socket.on('no_device', () => setHasDevice(false));

        socket.on('devices_update', (devices) => {
            const online = devices.filter(d => d.status === 'online').length;
            setHasDevice(online > 0);
        });

        socket.on('disconnect', () => setConnected(false));
        socket.on('connect_error', () => {
            setConnected(false);
            setHasDevice(false);
        });

        return () => socket.disconnect();
    }, [addLog, addAnomaly]);

    return {
        connected, hasDevice, logs, anomalies,
        foreground, socket: socketRef.current,
    };
}
