export const devices = [
    { id: 1, name: 'Pixel 7 Pro', serial: 'ADB-192.168.1.45', status: 'online' },
    { id: 2, name: 'Samsung S23', serial: 'ADB-USBC-0042', status: 'online' },
    { id: 3, name: 'OnePlus 11', serial: 'ADB-USBC-9981', status: 'offline' },
    { id: 4, name: 'Xiaomi 13', serial: 'ADB-WIFI-7712', status: 'online' },
];

export const appNames = [
    'com.android.chrome',
    'com.whatsapp',
    'com.instagram.android',
    'com.google.android.youtube',
    'com.google.android.gm',
    'com.android.settings',
    'com.crypto.ledger',
    'system_server',
    'com.android.systemui',
    'com.android.bluetooth',
    'Unknown-1029',
    'com.telegram.messenger',
];

export const eventTypes = [
    'API Call',
    'File Access',
    'Network Request',
    'Permission Update',
    'Process Fork',
    'Socket Open',
    'Auth Attempt',
    'Buffer Overflow Attempt',
    'Process Start',
    'Network Socket Open',
    'Camera Access',
    'Microphone Access',
    'Location Query',
    'SMS Read',
];

export const severities = ['LOW', 'MEDIUM', 'CRITICAL'];

export function generateLogEntry() {
    const now = new Date();
    const ts = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');
    return {
        id: Date.now() + Math.random(),
        timestamp: ts,
        appName: appNames[Math.floor(Math.random() * appNames.length)],
        eventType: eventTypes[Math.floor(Math.random() * eventTypes.length)],
        severity: severities[Math.floor(Math.random() * severities.length)],
    };
}
