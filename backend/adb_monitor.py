import subprocess
import re
import os

# Path to adb.exe on this system
ADB_PATH = r"C:\Users\melvi\Downloads\platform-tools\adb.exe"

# Known spyware / suspicious package patterns
SPYWARE_PATTERNS = [
    'com.spy', 'com.hidden', 'com.track', 'com.monitor', 'com.stealth',
    'com.keylog', 'com.surveil', 'org.spyware', 'net.spy', 'com.mspy',
    'com.flexispy', 'com.cocospy', 'com.hoverwatch', 'com.cerberus',
    'com.thetruthspy', 'com.xnspy', 'com.ikey', 'com.ikeymonitor',
]

# Human-readable names for common Android system processes/tags
FRIENDLY_NAMES = {
    # Core Android System
    'dumpsys': 'System Diagnostics',
    'SurfaceFlinger': 'Display Renderer',
    'ActivityManager': 'App Manager',
    'ActivityTaskManager': 'App Task Manager',
    'PackageManager': 'Package Installer',
    'WindowManager': 'Window Manager',
    'InputDispatcher': 'Touch Input Handler',
    'InputReader': 'Input Reader',
    'PowerManagerService': 'Power Manager',
    'BatteryStats': 'Battery Monitor',
    'BatteryDump': 'Battery Diagnostics',
    'ConnectivityManager': 'Network Manager',
    'ConnectivityService': 'Network Service',
    'WifiService': 'WiFi Service',
    'WifiHAL': 'WiFi Hardware Driver',
    'BluetoothAdapter': 'Bluetooth',
    'Telephony': 'Phone/Cellular',
    'TelephonyManager': 'Cellular Manager',
    'LocationManager': 'Location Service',
    'GnssLocationProvider': 'GPS Provider',
    'SensorService': 'Sensor Service',
    'CameraService': 'Camera Service',
    'AudioFlinger': 'Audio Engine',
    'MediaPlayerService': 'Media Player',
    'NotificationManager': 'Notifications',
    'AlarmManager': 'Alarm Scheduler',
    'JobScheduler': 'Background Jobs',
    'DownloadManager': 'Download Manager',
    'ContentResolver': 'Data Access Layer',
    'DatabaseUtils': 'Database Access',
    'SQLiteLog': 'Database Engine',
    'System.err': 'System Error',
    'System.out': 'System Output',
    'AndroidRuntime': 'Android Runtime',
    'art': 'Runtime Engine',
    'Zygote': 'App Process Launcher',
    'ServiceManager': 'Service Manager',
    'SystemServer': 'System Server',
    # Hardware / Vendor
    'thermal_core': 'Temperature Monitor',
    'thermal': 'Thermal Service',
    'io_stats': 'Disk I/O Monitor',
    'SemDvfsHyPerManager': 'CPU Performance Manager',
    'RefreshRateSelector': 'Screen Refresh Controller',
    'SyncManager': 'Data Sync Service',
    'SatelliteController': 'Satellite/GPS Controller',
    'ltm_mgr': 'Display Tone Manager',
    'Hal3ARaw': 'Camera Hardware Driver',
    'HYPER-HAL': 'Hardware Acceleration Layer',
    'HoneySpace.GestureInputHandler': 'Gesture Handler',
    'HoneySpace.InputSession': 'Input Session Manager',
    'idle_inject': 'CPU Idle Manager',
    'netd': 'Network Daemon',
    'vold': 'Storage Volume Daemon',
    'installd': 'App Installer Daemon',
    'logd': 'Log Service',
    'healthd': 'Device Health Monitor',
    # Google / Common Apps (by tag)
    'GooglePlayServicesUtil': 'Google Play Services',
    'GmsClient': 'Google Services',
    'Firebase': 'Firebase Analytics',
    'Volley': 'HTTP Network Library',
    'OkHttp': 'HTTP Client',
    'Retrofit': 'API Client',
    'Glide': 'Image Loader',
    'GCM': 'Push Notifications (Google)',
    'FCM': 'Push Notifications (Firebase)',
    'WebView': 'Built-in Browser',
    'chromium': 'Chrome Engine',
}

# Sensitive app categories for time-window enforcement
SENSITIVE_APPS = {
    'gallery': ['com.google.android.apps.photos', 'com.sec.android.gallery3d',
                'com.android.gallery', 'com.miui.gallery'],
    'camera': ['com.android.camera', 'com.sec.android.app.camera',
               'com.google.android.GoogleCamera', 'com.miui.camera'],
    'banking': ['com.google.android.apps.walletnfcrel', 'com.paypal',
                'com.venmo', 'com.cashapp', 'com.phonepe', 'com.paytm',
                'in.org.npci.upiapp', 'com.google.android.apps.nbu.paisa.user'],
    'messaging': ['com.whatsapp', 'org.telegram.messenger', 'com.Slack',
                  'com.discord', 'com.facebook.orca'],
    'file_manager': ['com.android.documentsui', 'com.google.android.apps.nbu.files',
                     'com.mi.android.globalFileexplorer'],
}


class ADBMonitor:
    """Connects to real Android devices using the local adb binary."""

    def __init__(self):
        self.adb = ADB_PATH
        if not os.path.exists(self.adb):
            print(f"[ADB] WARNING: adb.exe not found at {self.adb}")
            self.adb = "adb"  # Fallback to PATH
        self._start_server()

    def _run(self, *args, timeout=10):
        """Run an adb command and return stdout."""
        cmd = [self.adb] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            print(f"[ADB] adb binary not found")
            return ""
        except Exception as e:
            print(f"[ADB] Error: {e}")
            return ""

    def _start_server(self):
        """Start the ADB server."""
        self._run("start-server")
        print("[ADB] Server started")

    # ===== Layer 1: Device Discovery =====
    def get_devices(self):
        """List real connected devices with model and OS info."""
        raw = self._run("devices", "-l")
        if not raw:
            return []

        devices = []
        for line in raw.splitlines()[1:]:
            line = line.strip()
            if not line or "offline" in line:
                continue

            parts = line.split()
            serial = parts[0]
            status = "online" if "device" in parts[1] else parts[1]

            model = "Unknown"
            for part in parts:
                if part.startswith("model:"):
                    model = part.split(":", 1)[1].replace("_", " ")

            os_version = self._run("-s", serial, "shell", "getprop", "ro.build.version.release")
            os_version = f"Android {os_version}" if os_version else "Android ?"

            if model == "Unknown":
                m = self._run("-s", serial, "shell", "getprop", "ro.product.model")
                if m:
                    model = m

            devices.append({
                'serial': serial, 'model': model,
                'os_version': os_version,
                'status': status if status == 'online' else 'offline',
            })

        return devices

    # ===== Layer 2: Data Acquisition =====
    def get_logcat(self, serial, lines=20):
        """Get the latest N logcat lines from a device (real data)."""
        raw = self._run("-s", serial, "logcat", "-d", "-v", "brief", "-t", str(lines), timeout=8)
        if not raw:
            return []

        entries = []
        for line in raw.splitlines():
            parsed = self._parse_logcat_line(line)
            if parsed:
                entries.append(parsed)
        return entries

    def get_foreground_app(self, serial):
        """Get the currently visible foreground app using dumpsys activity."""
        # Try mResumedActivity first (Android 10+)
        raw = self._run("-s", serial, "shell",
                        "dumpsys activity activities | grep mResumedActivity", timeout=8)
        if raw:
            # Pattern: mResumedActivity: ActivityRecord{... com.example.app/.MainActivity ...}
            match = re.search(r'(\S+)/(\S+)', raw)
            if match:
                package = match.group(1)
                activity = match.group(2)
                return {
                    'package': package,
                    'activity': activity,
                    'label': self._get_app_label(serial, package),
                    'category': self._categorize_app(package),
                }

        # Fallback: try mCurrentFocus
        raw2 = self._run("-s", serial, "shell",
                         "dumpsys window | grep mCurrentFocus", timeout=8)
        if raw2:
            match = re.search(r'(\S+)/(\S+)', raw2)
            if match:
                package = match.group(1)
                activity = match.group(2)
                return {
                    'package': package,
                    'activity': activity,
                    'label': self._get_app_label(serial, package),
                    'category': self._categorize_app(package),
                }

        return None

    def get_running_processes(self, serial):
        """Get list of running processes with PID and user."""
        raw = self._run("-s", serial, "shell", "ps -A -o PID,USER,NAME", timeout=10)
        if not raw:
            return []

        processes = []
        for line in raw.splitlines()[1:]:  # Skip header
            parts = line.split(None, 2)
            if len(parts) >= 3:
                processes.append({
                    'pid': parts[0],
                    'user': parts[1],
                    'name': parts[2],
                })
        return processes

    def get_installed_packages(self, serial):
        """Get all installed packages for spyware scanning."""
        raw = self._run("-s", serial, "shell", "pm list packages -f", timeout=15)
        if not raw:
            return []

        packages = []
        for line in raw.splitlines():
            # Format: package:/data/app/com.example-xyz==/base.apk=com.example
            match = re.match(r'package:(.+?)=(.+)', line)
            if match:
                packages.append({
                    'path': match.group(1),
                    'package': match.group(2),
                    'is_suspicious': self._is_suspicious_package(match.group(2)),
                })
            else:
                # Simpler format: package:com.example
                cleaned = line.replace('package:', '').strip()
                if cleaned:
                    packages.append({
                        'path': '',
                        'package': cleaned,
                        'is_suspicious': self._is_suspicious_package(cleaned),
                    })
        return packages

    def get_battery_stats(self, serial):
        """Get battery info for device forensics."""
        raw = self._run("-s", serial, "shell", "dumpsys battery", timeout=8)
        stats = {}
        if raw:
            for line in raw.splitlines():
                if ':' in line:
                    key, _, val = line.partition(':')
                    stats[key.strip().lower().replace(' ', '_')] = val.strip()
        return stats

    # ===== Parsing & Classification =====
    def _parse_logcat_line(self, line):
        """Parse a logcat brief line into structured data."""
        match = re.match(r'^([VDIWEF])/(\S+)\s*\(\s*\d+\):\s*(.+)$', line)
        if not match:
            return None

        level = match.group(1)
        tag = match.group(2)
        message = match.group(3).strip()

        severity_map = {
            'V': 'LOW', 'D': 'LOW', 'I': 'LOW',
            'W': 'MEDIUM', 'E': 'CRITICAL', 'F': 'CRITICAL',
        }
        severity = severity_map.get(level, 'LOW')
        event_type = self._classify_event(tag, message)

        return {
            'app_name': self._friendly_name(tag),
            'event_type': event_type,
            'severity': severity,
            'raw': line,
        }

    def _friendly_name(self, tag):
        """Convert raw logcat tag to a human-readable name."""
        # 1. Exact match in dictionary
        if tag in FRIENDLY_NAMES:
            return FRIENDLY_NAMES[tag]

        # 2. Partial match (for tags like ORC/something)
        for key, friendly in FRIENDLY_NAMES.items():
            if key.lower() in tag.lower():
                return friendly

        # 3. Package name pattern (com.example.app → App)
        if '.' in tag and tag.count('.') >= 2:
            parts = tag.split('.')
            name = parts[-1]
            # Known company prefixes
            company_map = {
                'google': 'Google', 'samsung': 'Samsung', 'sec': 'Samsung',
                'android': 'Android', 'facebook': 'Facebook', 'meta': 'Meta',
                'whatsapp': 'WhatsApp', 'instagram': 'Instagram',
                'microsoft': 'Microsoft', 'apple': 'Apple',
            }
            company = ''
            for part in parts:
                if part.lower() in company_map:
                    company = company_map[part.lower()] + ' '
                    break
            clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
            clean = clean.replace('_', ' ').title()
            return f'{company}{clean}'.strip()

        # 4. CamelCase split (SurfaceFlinger → Surface Flinger)
        clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', tag)
        clean = clean.replace('_', ' ').replace('/', ' / ').title()
        return clean

    def _classify_event(self, tag, message):
        """Classify a logcat entry into a forensic event type."""
        msg_lower = message.lower()
        tag_lower = tag.lower()

        if any(k in msg_lower for k in ['permission', 'grant', 'deny', 'revoke']):
            return 'Permission Update'
        if any(k in msg_lower for k in ['network', 'socket', 'connect', 'http', 'dns']):
            return 'Network Request'
        if any(k in msg_lower for k in ['file', 'open', 'read', 'write', 'storage']):
            return 'File Access'
        if any(k in msg_lower for k in ['camera']):
            return 'Camera Access'
        if any(k in msg_lower for k in ['microphone', 'audio', 'record']):
            return 'Microphone Access'
        if any(k in msg_lower for k in ['location', 'gps', 'geofence']):
            return 'Location Query'
        if any(k in msg_lower for k in ['sms', 'message', 'telephony']):
            return 'SMS Access'
        if any(k in msg_lower for k in ['auth', 'login', 'password', 'credential']):
            return 'Auth Attempt'
        if any(k in msg_lower for k in ['crash', 'exception', 'fatal', 'anr']):
            return 'Crash/ANR'
        if any(k in msg_lower for k in ['process', 'fork', 'exec', 'kill']):
            return 'Process Event'
        if any(k in tag_lower for k in ['activity', 'activitymanager']):
            return 'Activity Lifecycle'
        if any(k in tag_lower for k in ['packagemanager', 'install']):
            return 'Package Event'
        return 'System Event'

    def _get_app_label(self, serial, package):
        """Try to get a human-readable app label from package name."""
        # Extract meaningful name from package
        parts = package.split('.')
        if len(parts) >= 3:
            return parts[-1].replace('_', ' ').title()
        return package

    def _categorize_app(self, package):
        """Categorize app into sensitive categories."""
        pkg_lower = package.lower()
        for category, patterns in SENSITIVE_APPS.items():
            for pat in patterns:
                if pat.lower() in pkg_lower or pkg_lower in pat.lower():
                    return category
        if self._is_suspicious_package(package):
            return 'suspicious'
        return 'normal'

    def _is_suspicious_package(self, package):
        """Check if a package name matches known spyware patterns."""
        pkg_lower = package.lower()
        return any(pat in pkg_lower for pat in SPYWARE_PATTERNS)

    def get_dumpsys(self, serial, service="activity"):
        """Run dumpsys on a device."""
        return self._run("-s", serial, "shell", "dumpsys", service, timeout=15)


# Singleton
adb_monitor = ADBMonitor()
