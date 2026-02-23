import os
import io
from datetime import datetime
from flask import Flask, jsonify, send_file, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from fpdf import FPDF
import models as m
from models import db, AndroidDevice, ActivityLog, Alert, Baseline, ForegroundSnapshot
from adb_monitor import adb_monitor
from behavior_engine import BehaviorEngine
from email_notifier import send_alert_email, is_configured as email_configured

app = Flask(__name__, static_folder='static', static_url_path='/')
CORS(app)

@app.route('/')
def serve_index():
    return send_file(os.path.join(app.static_folder, 'index.html'))

@app.errorhandler(404)
def not_found(e):
    return send_file(os.path.join(app.static_folder, 'index.html'))

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///adb_forensics.db')
# Render uses postgres:// which SQLAlchemy 1.4+ requires to be postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'forensic-secret-key')

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ===== Mock Data for Render Demo =====
def background_mock_stream():
    """Generates fake logs if running on Render for demo purposes."""
    import random
    import time
    with app.app_context():
        # Ensure at least one dummy device exists
        if not AndroidDevice.query.first():
            db.session.add(AndroidDevice(serial='RENDER-DEMO-001', model='Virtual Pixel 7', status='online'))
            db.session.commit()
            
        device = AndroidDevice.query.first()
        apps_list = ['System UI', 'WhatsApp', 'Chrome', 'Banking App', 'Settings', 'Telegram', 'Instagram']
        events_list = ['Network Request', 'File Access', 'Permission Update', 'Process Event', 'Camera Access']
        
        while True:
            try:
                now = datetime.utcnow()
                app_choice = random.choice(apps_list)
                event_choice = random.choice(events_list)
                # Randomly choose severity (CRITICAL is 10% chance)
                severity = 'LOW' if random.random() > 0.15 else 'CRITICAL'
                
                log = ActivityLog(
                    device_id=device.id, timestamp=now,
                    app_name=app_choice, event_type=event_choice,
                    severity=severity, raw_data=f"Demo: Observed {event_choice} from {app_choice}",
                    is_anomaly=(severity == 'CRITICAL'),
                )
                db.session.add(log)
                if severity == 'CRITICAL':
                    db.session.add(Alert(alert_type='Unauthorized Activity', 
                                       description=f"Demo: Critical {event_choice} in {app_choice}", 
                                       severity='CRITICAL'))
                db.session.commit()
                
                socketio.emit('new_log', {
                    'id': log.id, 'timestamp': now.isoformat() + 'Z',
                    'app_name': app_choice, 'event_type': event_choice,
                    'severity': severity, 'is_anomaly': (severity == 'CRITICAL'),
                    'source': 'render_demo',
                })
                
                # Periodically update stats
                socketio.emit('stats_update', compute_stats())
                
            except Exception as e:
                print(f"Mock error: {e}")
            socketio.sleep(random.randint(2, 5))

last_seen_raw = set()
behavior_engine = None  # Initialized after app context

# ===== Device Discovery =====
def sync_real_devices():
    real_devices = adb_monitor.get_devices()
    AndroidDevice.query.update({AndroidDevice.status: 'disconnected'})
    if real_devices:
        print(f"[ADB] Found {len(real_devices)} real device(s): {[d['model'] for d in real_devices]}")
        for dev in real_devices:
            existing = AndroidDevice.query.filter_by(serial=dev['serial']).first()
            if existing:
                existing.model = dev['model']
                existing.os_version = dev['os_version']
                existing.status = dev['status']
                existing.last_seen = datetime.utcnow()
            else:
                db.session.add(AndroidDevice(
                    serial=dev['serial'], model=dev['model'],
                    os_version=dev['os_version'], status=dev['status'],
                    last_seen=datetime.utcnow(),
                ))
        db.session.commit()
        return True
    else:
        db.session.commit()
        return False

def compute_stats():
    total_logs = ActivityLog.query.count()
    alert_count = Alert.query.filter_by(resolved=False).count()
    online_devices = AndroidDevice.query.filter_by(status='online').count()
    recent_critical = ActivityLog.query.filter_by(severity='CRITICAL').limit(50).count()
    if total_logs == 0:
        threat = 'LOW'
    else:
        ratio = recent_critical / min(total_logs, 50)
        if ratio > 0.4: threat = 'CRITICAL'
        elif ratio > 0.25: threat = 'HIGH'
        elif ratio > 0.1: threat = 'ELEVATED'
        else: threat = 'LOW'

    active_procs = 0
    devices = AndroidDevice.query.filter_by(status='online').all()
    if devices:
        try:
            output = adb_monitor._run("-s", devices[0].serial, "shell",
                                       "ps -A | wc -l", timeout=5)
            if output.strip().isdigit():
                active_procs = int(output.strip())
        except:
            pass

    return {
        'totalLogs': total_logs, 'activeProcesses': active_procs,
        'threatLevel': threat, 'alert_count': alert_count,
        'onlineDevices': online_devices,
        'emailConfigured': email_configured(),
    }

# ===== API Routes =====
@app.route('/api/devices')
def get_devices():
    devices = AndroidDevice.query.all()
    return jsonify([{
        'id': d.id, 'serial': d.serial, 'model': d.model,
        'os_version': d.os_version, 'status': d.status,
        'last_seen': d.last_seen.isoformat() if d.last_seen else None,
    } for d in devices])

@app.route('/api/devices/refresh')
def refresh_devices():
    found = sync_real_devices()
    devices = AndroidDevice.query.all()
    return jsonify({
        'found': found, 'count': len(devices),
        'devices': [{'id': d.id, 'serial': d.serial, 'model': d.model, 'status': d.status} for d in devices]
    })

@app.route('/api/logs')
def get_logs():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': l.id,
        'timestamp': l.timestamp.isoformat() + 'Z',
        'app_name': l.app_name, 'event_type': l.event_type,
        'severity': l.severity, 'is_anomaly': l.is_anomaly,
    } for l in logs])

@app.route('/api/alerts')
def get_alerts():
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(50).all()
    return jsonify([{
        'id': a.id, 'alert_type': a.alert_type, 'description': a.description,
        'created_at': a.created_at.isoformat(), 'resolved': a.resolved,
        'severity': a.severity,
    } for a in alerts])

@app.route('/api/stats')
def get_stats():
    return jsonify(compute_stats())

@app.route('/api/baseline')
def get_baseline():
    device = AndroidDevice.query.filter_by(status='online').first()
    if not device:
        return jsonify({'baselines': [], 'message': 'No online device'})
    baselines = behavior_engine.get_baseline(device.id) if behavior_engine else []
    return jsonify({'device_id': device.id, 'baselines': baselines})

@app.route('/api/baseline/configure', methods=['POST'])
def configure_baseline():
    data = request.json
    device_id = data.get('device_id')
    app_name = data.get('app_name')
    is_whitelisted = data.get('is_whitelisted', True)
    start_hour = data.get('start_hour', 9)
    end_hour = data.get('end_hour', 18)

    entry = Baseline.query.filter_by(device_id=device_id, app_name=app_name).first()
    if entry:
        entry.is_whitelisted = is_whitelisted
        entry.typical_start_hour = start_hour
        entry.typical_end_hour = end_hour
    else:
        db.session.add(Baseline(
            device_id=device_id, app_name=app_name,
            is_whitelisted=is_whitelisted,
            typical_start_hour=start_hour, typical_end_hour=end_hour,
        ))
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/anomalies')
def get_anomalies():
    alerts = Alert.query.filter(
        Alert.severity.in_(['HIGH', 'CRITICAL'])
    ).order_by(Alert.created_at.desc()).limit(30).all()
    return jsonify([{
        'id': a.id, 'alert_type': a.alert_type, 'description': a.description,
        'created_at': a.created_at.isoformat(), 'severity': a.severity,
        'resolved': a.resolved,
    } for a in alerts])

# ===== Export Endpoints =====
@app.route('/api/export/sqlite')
def export_sqlite():
    db_path = os.path.join(app.instance_path, 'adb_forensics.db')
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True,
                        download_name=f'adb_forensics_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.db',
                        mimetype='application/x-sqlite3')
    return jsonify({'error': 'Database file not found'}), 404

@app.route('/api/export/pdf')
def export_pdf():
    """Generate a Legal-Ready Digital Forensic Report in PDF format."""
    stats = compute_stats()
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(200).all()
    devices = AndroidDevice.query.all()
    alerts = Alert.query.filter_by(resolved=False).all()
    now = datetime.utcnow()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Cover Page ---
    pdf.add_page()
    pdf.set_fill_color(10, 17, 24)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(0, 242, 255)
    pdf.cell(0, 80, '', ln=True)
    pdf.cell(0, 15, 'DIGITAL FORENSIC REPORT', ln=True, align='C')
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(224, 230, 237)
    pdf.cell(0, 10, 'Enhanced ADB Forensic Monitor', ln=True, align='C')
    pdf.cell(0, 8, '', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 8, f'Generated: {now.strftime("%Y-%m-%d %H:%M:%S UTC")}', ln=True, align='C')
    pdf.cell(0, 8, f'Classification: CONFIDENTIAL', ln=True, align='C')
    pdf.cell(0, 8, f'Threat Level: {stats["threatLevel"]}', ln=True, align='C')
    pdf.cell(0, 40, '', ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, 'This report is generated automatically by the Enhanced ADB Forensic Monitor.', ln=True, align='C')
    pdf.cell(0, 6, 'All timestamps are in UTC. This document may be used as digital evidence.', ln=True, align='C')

    # --- Executive Summary ---
    pdf.add_page()
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 12, 'EXECUTIVE SUMMARY', ln=True)
    pdf.set_draw_color(0, 200, 220)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.cell(0, 6, '', ln=True)

    pdf.set_font('Helvetica', '', 11)
    summary_items = [
        f"Report Date: {now.strftime('%B %d, %Y at %H:%M UTC')}",
        f"Total Logs Captured: {stats['totalLogs']}",
        f"Active Processes: {stats['activeProcesses']}",
        f"Unresolved Alerts: {stats['alert_count']}",
        f"Current Threat Level: {stats['threatLevel']}",
        f"Online Devices: {stats['onlineDevices']}",
        f"Email Alerts: {'Configured' if stats['emailConfigured'] else 'Not Configured'}",
    ]
    for item in summary_items:
        pdf.cell(0, 8, f'  * {item}', ln=True)

    # --- Device Inventory ---
    pdf.cell(0, 10, '', ln=True)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 12, 'DEVICE INVENTORY', ln=True)
    pdf.set_draw_color(0, 200, 220)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.cell(0, 4, '', ln=True)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(230, 240, 245)
    pdf.cell(40, 8, 'STATUS', 1, 0, 'C', fill=True)
    pdf.cell(50, 8, 'MODEL', 1, 0, 'C', fill=True)
    pdf.cell(50, 8, 'SERIAL', 1, 0, 'C', fill=True)
    pdf.cell(45, 8, 'OS VERSION', 1, 1, 'C', fill=True)

    pdf.set_font('Helvetica', '', 9)
    for d in devices:
        pdf.cell(40, 7, d.status.upper() if d.status else '-', 1, 0, 'C')
        pdf.cell(50, 7, (d.model or '-')[:25], 1, 0, 'C')
        pdf.cell(50, 7, (d.serial or '-')[:25], 1, 0, 'C')
        pdf.cell(45, 7, (d.os_version or '-')[:20], 1, 1, 'C')

    # --- Alert Summary ---
    pdf.cell(0, 10, '', ln=True)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 12, 'UNRESOLVED ALERTS', ln=True)
    pdf.set_draw_color(0, 200, 220)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.cell(0, 4, '', ln=True)

    if alerts:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(255, 235, 235)
        pdf.cell(35, 8, 'SEVERITY', 1, 0, 'C', fill=True)
        pdf.cell(50, 8, 'TYPE', 1, 0, 'C', fill=True)
        pdf.cell(100, 8, 'DESCRIPTION', 1, 1, 'C', fill=True)

        pdf.set_font('Helvetica', '', 8)
        for a in alerts[:30]:
            pdf.cell(35, 7, (a.severity or 'HIGH'), 1, 0, 'C')
            pdf.cell(50, 7, (a.alert_type or '-')[:25], 1, 0, 'C')
            pdf.cell(100, 7, (a.description or '-')[:55], 1, 1)
    else:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 8, 'No unresolved alerts.', ln=True)

    # --- Timeline of Events ---
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 12, 'TIMELINE OF EVENTS (Recent 200)', ln=True)
    pdf.set_draw_color(0, 200, 220)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.cell(0, 4, '', ln=True)

    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(230, 240, 245)
    pdf.cell(30, 7, 'TIMESTAMP', 1, 0, 'C', fill=True)
    pdf.cell(55, 7, 'APP / PROCESS', 1, 0, 'C', fill=True)
    pdf.cell(55, 7, 'ACTIVITY TYPE', 1, 0, 'C', fill=True)
    pdf.cell(25, 7, 'SEVERITY', 1, 0, 'C', fill=True)
    pdf.cell(20, 7, 'ANOMALY', 1, 1, 'C', fill=True)

    pdf.set_font('Helvetica', '', 7)
    for log in logs:
        ts = log.timestamp.strftime('%H:%M:%S')
        app_name = (log.app_name or '-')[:28]
        event = (log.event_type or '-')[:28]
        sev = (log.severity or '-')
        anom = 'YES' if log.is_anomaly else ''

        if log.is_anomaly:
            pdf.set_fill_color(255, 245, 245)
            fill = True
        else:
            fill = False

        pdf.cell(30, 6, ts, 1, 0, 'C', fill=fill)
        pdf.cell(55, 6, app_name, 1, 0, '', fill=fill)
        pdf.cell(55, 6, event, 1, 0, '', fill=fill)
        pdf.cell(25, 6, sev, 1, 0, 'C', fill=fill)
        pdf.cell(20, 6, anom, 1, 1, 'C', fill=fill)

    # --- Chain of Custody Footer ---
    pdf.cell(0, 12, '', ln=True)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'CHAIN OF CUSTODY', ln=True)
    pdf.set_draw_color(0, 200, 220)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.cell(0, 4, '', ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 7, f'Report generated by: Enhanced ADB Forensic Monitor (Automated)', ln=True)
    pdf.cell(0, 7, f'Timestamp: {now.strftime("%Y-%m-%d %H:%M:%S UTC")}', ln=True)
    pdf.cell(0, 7, f'System: Forensic Analysis Workstation', ln=True)
    pdf.cell(0, 7, f'Integrity: This report is auto-generated and has not been manually altered.', ln=True)
    pdf.cell(0, 12, '', ln=True)
    pdf.cell(0, 7, 'Examiner Signature: ________________________    Date: ____________', ln=True)
    pdf.cell(0, 7, 'Reviewer Signature: ________________________    Date: ____________', ln=True)

    # Output
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                    download_name=f'forensic_report_{now.strftime("%Y%m%d_%H%M%S")}.pdf',
                    mimetype='application/pdf')

# ===== WebSocket Events =====
@socketio.on('connect')
def handle_connect():
    online = AndroidDevice.query.filter_by(status='online').count()
    mode = 'live' if online > 0 else 'no_devices'
    print(f'[WS] Client connected (mode={mode})')
    emit('status', {'data': 'Connected to ADB Forensic Backend', 'mode': mode})

@socketio.on('disconnect')
def handle_disconnect():
    print('[WS] Client disconnected')

# ===== Background Tasks =====
def background_device_scanner():
    with app.app_context():
        while True:
            try:
                sync_real_devices()
                devices = AndroidDevice.query.all()
                socketio.emit('devices_update', [{
                    'id': d.id, 'serial': d.serial, 'model': d.model,
                    'os_version': d.os_version, 'status': d.status,
                } for d in devices])
            except Exception as e:
                print(f"[SCAN] Error: {e}")
            socketio.sleep(10)

def background_stats_emitter():
    with app.app_context():
        while True:
            try:
                stats = compute_stats()
                socketio.emit('stats_update', stats)
            except Exception as e:
                print(f"[STATS] Error: {e}")
            socketio.sleep(5)

def background_log_stream():
    """Stream REAL logcat data from connected devices."""
    global last_seen_raw
    with app.app_context():
        while True:
            online_devices = AndroidDevice.query.filter_by(status='online').all()
            if not online_devices:
                socketio.emit('no_device', {'message': 'No devices connected.'})
                socketio.sleep(3)
                continue

            for device in online_devices:
                try:
                    entries = adb_monitor.get_logcat(device.serial, lines=10)
                    for entry in entries:
                        raw_hash = hash(entry['raw'])
                        if raw_hash in last_seen_raw:
                            continue
                        last_seen_raw.add(raw_hash)
                        if len(last_seen_raw) > 5000:
                            last_seen_raw = set(list(last_seen_raw)[-2000:])

                        now = datetime.utcnow()
                        is_anomaly = entry['severity'] == 'CRITICAL'
                        log = ActivityLog(
                            device_id=device.id, timestamp=now,
                            app_name=entry['app_name'], event_type=entry['event_type'],
                            severity=entry['severity'], raw_data=entry['raw'],
                            is_anomaly=is_anomaly,
                        )
                        db.session.add(log)

                        if is_anomaly:
                            db.session.flush()
                            db.session.add(Alert(
                                log_id=log.id, alert_type='Unauthorized Activity',
                                description=f"Critical: {entry['event_type']} from {entry['app_name']}",
                                severity='CRITICAL',
                            ))
                        db.session.commit()

                        socketio.emit('new_log', {
                            'id': log.id, 'timestamp': now.isoformat() + 'Z',
                            'app_name': entry['app_name'], 'event_type': entry['event_type'],
                            'severity': entry['severity'], 'is_anomaly': is_anomaly,
                            'source': 'adb_logcat',
                        })
                except Exception as e:
                    print(f"[LOGCAT] Error: {e}")

            socketio.sleep(2)

def background_foreground_tracker():
    """Track foreground apps every 5 seconds and analyze via behavior engine."""
    with app.app_context():
        while True:
            online_devices = AndroidDevice.query.filter_by(status='online').all()
            for device in online_devices:
                try:
                    fg = adb_monitor.get_foreground_app(device.serial)
                    if fg:
                        # Save snapshot
                        snap = ForegroundSnapshot(
                            device_id=device.id,
                            package_name=fg['package'],
                            app_label=fg['label'],
                            category=fg['category'],
                            timestamp=datetime.utcnow(),
                        )
                        db.session.add(snap)
                        db.session.commit()

                        # Emit to frontend
                        socketio.emit('foreground_update', {
                            'device_id': device.id,
                            'package': fg['package'],
                            'label': fg['label'],
                            'category': fg['category'],
                        })

                        # Run behavior analysis
                        if behavior_engine:
                            anomalies = behavior_engine.analyze_foreground(device.id, fg)
                            for anom in anomalies:
                                # Save anomaly alert
                                alert = Alert(
                                    alert_type=anom['type'],
                                    description=anom['description'],
                                    severity=anom['severity'],
                                )
                                db.session.add(alert)
                                db.session.commit()

                                # Push to frontend
                                socketio.emit('anomaly_detected', {
                                    'id': alert.id,
                                    'type': anom['type'],
                                    'severity': anom['severity'],
                                    'description': anom['description'],
                                    'package': anom.get('package', ''),
                                    'category': anom.get('category', ''),
                                    'timestamp': datetime.utcnow().strftime('%H:%M:%S'),
                                })

                                # Send email for critical anomalies
                                if anom['severity'] in ('HIGH', 'CRITICAL'):
                                    send_alert_email(
                                        anom['type'], anom['description'],
                                        anom['severity'],
                                        {'model': device.model, 'serial': device.serial}
                                    )

                except Exception as e:
                    print(f"[FOREGROUND] Error: {e}")

            socketio.sleep(5)

def background_behavior_analyzer():
    """Run spyware scan and baseline updates every 30 seconds."""
    with app.app_context():
        while True:
            online_devices = AndroidDevice.query.filter_by(status='online').all()
            for device in online_devices:
                try:
                    # Update baseline from recent logs
                    if behavior_engine:
                        behavior_engine.update_baseline(device.id)

                    # Scan installed packages for spyware
                    packages = adb_monitor.get_installed_packages(device.serial)
                    processes = adb_monitor.get_running_processes(device.serial)

                    if behavior_engine:
                        threats = behavior_engine.scan_for_threats(packages, processes)
                        for threat in threats:
                            # Check if already reported recently
                            existing = Alert.query.filter_by(
                                description=threat['description'],
                                resolved=False,
                            ).first()
                            if existing:
                                continue

                            alert = Alert(
                                alert_type=threat['type'],
                                description=threat['description'],
                                severity=threat['severity'],
                            )
                            db.session.add(alert)
                            db.session.commit()

                            socketio.emit('anomaly_detected', {
                                'id': alert.id,
                                'type': threat['type'],
                                'severity': threat['severity'],
                                'description': threat['description'],
                                'package': threat.get('package', ''),
                                'category': threat.get('category', ''),
                                'timestamp': datetime.utcnow().strftime('%H:%M:%S'),
                            })

                            if threat['severity'] == 'CRITICAL':
                                send_alert_email(
                                    threat['type'], threat['description'],
                                    threat['severity'],
                                    {'model': device.model, 'serial': device.serial}
                                )

                except Exception as e:
                    print(f"[BEHAVIOR] Error: {e}")

            socketio.sleep(30)

# ===== Entry Point =====
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        behavior_engine = BehaviorEngine(db, m)
    if os.environ.get('RENDER'):
        socketio.start_background_task(background_mock_stream)
        print('[RENDER] Running in Demo Mode with Mock Data')
    else:
        sync_real_devices()
        socketio.start_background_task(background_device_scanner)
        socketio.start_background_task(background_log_stream)
        socketio.start_background_task(background_stats_emitter)
        socketio.start_background_task(background_foreground_tracker)
        socketio.start_background_task(background_behavior_analyzer)
    
    print('[SERVER] Enhanced ADB Forensic Monitor running')
    socketio.run(app, debug=False, port=5000, host='0.0.0.0')
