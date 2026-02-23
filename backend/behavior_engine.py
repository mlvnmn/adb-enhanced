"""
Layer 3: Behavior Analysis Engine
- BaselineProfiler: learns normal app usage patterns
- RealtimeComparator: checks live data against baseline
- AnomalyDetector: flags unauthorized or suspicious behavior
"""
from datetime import datetime, timedelta


# Default work hours (can be overridden via API)
DEFAULT_WORK_START = 9    # 9 AM
DEFAULT_WORK_END = 18     # 6 PM

# Severity levels for anomalies
SEVERITY_INFO = 'LOW'
SEVERITY_WARN = 'MEDIUM'
SEVERITY_HIGH = 'HIGH'
SEVERITY_CRITICAL = 'CRITICAL'


class BaselineProfiler:
    """Learns what 'normal' looks like for a device."""

    def __init__(self, db, Baseline, ActivityLog):
        self.db = db
        self.Baseline = Baseline
        self.ActivityLog = ActivityLog

    def learn_from_logs(self, device_id, lookback_hours=72):
        """Analyze recent logs to build/update baseline for a device."""
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        logs = self.ActivityLog.query.filter(
            self.ActivityLog.device_id == device_id,
            self.ActivityLog.timestamp >= cutoff,
        ).all()

        if not logs:
            return

        # Count app usage
        app_counts = {}
        for log in logs:
            app = log.app_name or 'unknown'
            if app not in app_counts:
                app_counts[app] = {'count': 0, 'hours': set()}
            app_counts[app]['count'] += 1
            app_counts[app]['hours'].add(log.timestamp.hour)

        # Update or create baseline entries
        for app_name, stats in app_counts.items():
            existing = self.Baseline.query.filter_by(
                device_id=device_id, app_name=app_name
            ).first()

            hours = sorted(stats['hours'])
            start_h = hours[0] if hours else DEFAULT_WORK_START
            end_h = hours[-1] if hours else DEFAULT_WORK_END

            if existing:
                existing.times_seen = stats['count']
                existing.typical_start_hour = min(existing.typical_start_hour, start_h)
                existing.typical_end_hour = max(existing.typical_end_hour, end_h)
                existing.last_seen = datetime.utcnow()
            else:
                self.db.session.add(self.Baseline(
                    device_id=device_id,
                    app_name=app_name,
                    typical_start_hour=start_h,
                    typical_end_hour=end_h,
                    is_whitelisted=True,  # Auto-whitelist newly seen apps
                    times_seen=stats['count'],
                    last_seen=datetime.utcnow(),
                ))

        self.db.session.commit()

    def get_baseline(self, device_id):
        """Get current baseline for a device."""
        entries = self.Baseline.query.filter_by(device_id=device_id).all()
        return [{
            'app_name': b.app_name,
            'times_seen': b.times_seen,
            'typical_hours': f"{b.typical_start_hour}:00 - {b.typical_end_hour}:00",
            'is_whitelisted': b.is_whitelisted,
        } for b in entries]


class RealtimeComparator:
    """Compares live ADB data against the learned baseline."""

    def __init__(self, db, Baseline):
        self.db = db
        self.Baseline = Baseline

    def check_foreground_app(self, device_id, fg_info, current_hour=None):
        """
        Compare the current foreground app against baseline.
        Returns list of anomaly dicts if violations are found.
        """
        if not fg_info:
            return []

        if current_hour is None:
            current_hour = datetime.utcnow().hour

        anomalies = []
        package = fg_info.get('package', '')
        category = fg_info.get('category', 'normal')
        label = fg_info.get('label', package)

        # Check if this app exists in the baseline
        baseline_entry = self.Baseline.query.filter_by(
            device_id=device_id, app_name=package
        ).first()

        # --- Check 1: Never-before-seen app ---
        if not baseline_entry:
            anomalies.append({
                'type': 'Unknown Application',
                'severity': SEVERITY_WARN,
                'description': f"New app '{label}' ({package}) not in learned baseline",
                'package': package,
                'category': category,
            })

        # --- Check 2: App used outside allowed hours ---
        if baseline_entry and not baseline_entry.is_whitelisted:
            anomalies.append({
                'type': 'Blacklisted Application',
                'severity': SEVERITY_CRITICAL,
                'description': f"Blacklisted app '{label}' ({package}) was opened",
                'package': package,
                'category': category,
            })
        elif baseline_entry:
            start = baseline_entry.typical_start_hour
            end = baseline_entry.typical_end_hour
            if not (start <= current_hour <= end):
                anomalies.append({
                    'type': 'Off-Hours Activity',
                    'severity': SEVERITY_HIGH,
                    'description': (
                        f"App '{label}' opened at {current_hour}:00 — "
                        f"normal hours are {start}:00-{end}:00"
                    ),
                    'package': package,
                    'category': category,
                })

        # --- Check 3: Sensitive app usage ---
        if category in ('banking', 'gallery', 'camera'):
            anomalies.append({
                'type': 'Sensitive App Access',
                'severity': SEVERITY_HIGH,
                'description': f"Sensitive {category} app '{label}' ({package}) is active",
                'package': package,
                'category': category,
            })

        return anomalies


class AnomalyDetector:
    """Scans for spyware and unauthorized packages."""

    def scan_packages(self, installed_packages):
        """Scan installed packages for known spyware patterns."""
        anomalies = []
        for pkg in installed_packages:
            if pkg.get('is_suspicious'):
                anomalies.append({
                    'type': 'Spyware Detected',
                    'severity': SEVERITY_CRITICAL,
                    'description': f"Suspicious package detected: {pkg['package']}",
                    'package': pkg['package'],
                    'category': 'spyware',
                })
        return anomalies

    def scan_processes(self, processes, known_apps=None):
        """Check running processes for suspicious activity."""
        anomalies = []
        suspicious_patterns = ['spy', 'keylog', 'monitor', 'hidden', 'stealth', 'inject']

        for proc in processes:
            name = proc.get('name', '').lower()
            if any(pat in name for pat in suspicious_patterns):
                anomalies.append({
                    'type': 'Suspicious Process',
                    'severity': SEVERITY_CRITICAL,
                    'description': f"Suspicious process running: {proc['name']} (PID: {proc['pid']})",
                    'package': proc['name'],
                    'category': 'suspicious',
                })

        return anomalies


class BehaviorEngine:
    """Unified interface for the behavior analysis layer."""

    def __init__(self, db, models):
        self.profiler = BaselineProfiler(db, models.Baseline, models.ActivityLog)
        self.comparator = RealtimeComparator(db, models.Baseline)
        self.detector = AnomalyDetector()

    def analyze_foreground(self, device_id, fg_info):
        """Analyze current foreground app against baseline."""
        return self.comparator.check_foreground_app(device_id, fg_info)

    def scan_for_threats(self, packages, processes):
        """Run spyware and suspicious process scans."""
        anomalies = []
        anomalies.extend(self.detector.scan_packages(packages))
        anomalies.extend(self.detector.scan_processes(processes))
        return anomalies

    def update_baseline(self, device_id):
        """Refresh baseline from recent logs."""
        self.profiler.learn_from_logs(device_id)

    def get_baseline(self, device_id):
        """Get current baseline for a device."""
        return self.profiler.get_baseline(device_id)
