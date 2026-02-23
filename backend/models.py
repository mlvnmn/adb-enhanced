from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='analyst')


class AndroidDevice(db.Model):
    __tablename__ = 'android_devices'
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(100), unique=True, nullable=False)
    model = db.Column(db.String(100))
    os_version = db.Column(db.String(20))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='disconnected')


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('android_devices.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    app_name = db.Column(db.String(200))
    event_type = db.Column(db.String(100))
    severity = db.Column(db.String(20))
    raw_data = db.Column(db.Text)
    is_anomaly = db.Column(db.Boolean, default=False)

    device = db.relationship('AndroidDevice', backref=db.backref('logs', lazy=True))


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('activity_logs.id'), nullable=True)
    alert_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    severity = db.Column(db.String(20), default='HIGH')

    log = db.relationship('ActivityLog', backref=db.backref('alerts', lazy=True))


class Baseline(db.Model):
    """Stores learned normal usage patterns per device."""
    __tablename__ = 'baselines'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('android_devices.id'), nullable=False)
    app_name = db.Column(db.String(200))
    avg_daily_usage_minutes = db.Column(db.Float, default=0.0)
    typical_start_hour = db.Column(db.Integer, default=9)   # 24h format
    typical_end_hour = db.Column(db.Integer, default=18)     # 24h format
    is_whitelisted = db.Column(db.Boolean, default=True)
    times_seen = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    device = db.relationship('AndroidDevice', backref=db.backref('baselines', lazy=True))


class ForegroundSnapshot(db.Model):
    """Point-in-time foreground app snapshots."""
    __tablename__ = 'foreground_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('android_devices.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    package_name = db.Column(db.String(200))
    app_label = db.Column(db.String(200))
    category = db.Column(db.String(50), default='normal')

    device = db.relationship('AndroidDevice', backref=db.backref('foreground_snapshots', lazy=True))
