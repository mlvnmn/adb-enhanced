# Enhanced Unauthorized Mobile Device Usage Detection Tool
## Complete Presentation Guide

---

## 1. What is This Project?

A **real-time digital forensic monitoring tool** that connects to Android devices via USB, monitors all app activity using ADB (Android Debug Bridge), detects unauthorized or suspicious behavior, and generates legal-ready forensic reports — all through a professional cybersecurity dashboard.

**Use Case:** An organization wants to detect if employees are misusing company-issued phones — opening banking apps, installing spyware, using cameras during restricted hours, etc.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React.js + Vite | Interactive dashboard UI |
| **Styling** | Vanilla CSS (Glassmorphism) | Dark-themed forensic aesthetic |
| **Charts** | Chart.js + react-chartjs-2 | Real-time behavioral analysis graph |
| **Backend** | Python Flask | REST API server |
| **Real-time** | Flask-SocketIO (WebSockets) | Push live data to dashboard |
| **Database** | SQLite + SQLAlchemy ORM | Local forensic evidence storage |
| **Device Interface** | ADB (Android Debug Bridge) | Communicates with Android phone |
| **PDF Reports** | FPDF2 | Generates legal-ready forensic PDFs |
| **Email Alerts** | Python smtplib (SMTP) | Sends critical alert notifications |
| **Async Runtime** | Eventlet | Handles concurrent background tasks |

---

## 3. System Architecture (4-Layer Model)

```
┌──────────────────────────────────────────────────────┐
│                 LAYER 4: OUTPUT                       │
│  React Dashboard │ PDF Reports │ Email Notifications  │
├──────────────────────────────────────────────────────┤
│              LAYER 3: BEHAVIOR ENGINE                 │
│  Baseline Profiler │ Comparator │ Anomaly Detector    │
├──────────────────────────────────────────────────────┤
│           LAYER 2: DATA ACQUISITION                   │
│  adb logcat │ dumpsys activity │ ps -A │ pm list      │
├──────────────────────────────────────────────────────┤
│            LAYER 1: HARDWARE API                      │
│  ADB Bridge → USB Connection → Android Device         │
└──────────────────────────────────────────────────────┘
                        ↕
              ┌──────────────────┐
              │   SQLite Database │
              │   (6 Tables)      │
              └──────────────────┘
```

---

## 4. Layer-by-Layer Explanation

### Layer 1 & 2: Hardware API + Data Acquisition

**What it does:** Connects to a real Android phone via USB and continuously extracts data.

**ADB Commands Used:**

| Command | What It Captures |
|---------|-----------------|
| `adb logcat` | Live system logs — every app event, crash, permission request |
| `dumpsys activity` | Currently active foreground app (what's on screen right now) |
| `ps -A` | All running processes with PIDs |
| `pm list packages` | Every installed app — used to detect spyware |
| `dumpsys battery` | Battery stats for forensic context |

**Key File:** `adb_monitor.py` — The `ADBMonitor` class wraps these commands, parses the raw output, and classifies each event (e.g., "Network Request", "Camera Access", "File Access").

**How logcat parsing works:**
```
Raw line:    E/thermal_core(1234): File open: /sys/class/thermal
Parsed as:   severity=CRITICAL, app=thermal_core, type=File Access
```

---

### Layer 3: Behavior Analysis Engine

**What it does:** The "brain" — learns what's normal, then flags anything abnormal.

**Three components:**

**a) BaselineProfiler**
- Analyzes the last 72 hours of logs
- Learns which apps are "normal" for this device
- Records typical usage hours per app
- Auto-whitelists frequently seen apps

**b) RealtimeComparator** — Runs every 5 seconds, checks:
- ⚠️ Is this a **never-before-seen app**? → Flag as "Unknown Application"
- ⚠️ Is this app being used **outside normal hours**? → Flag as "Off-Hours Activity"
- ⚠️ Is this a **sensitive app** (banking, camera, gallery)? → Flag as "Sensitive App Access"
- 🚫 Is this app **blacklisted**? → Flag as "Blacklisted Application"

**c) AnomalyDetector** — Runs every 30 seconds:
- Scans all installed packages against **18 known spyware patterns** (FlexiSpy, mSpy, Cerberus, etc.)
- Scans running processes for suspicious names (keylogger, monitor, stealth, inject)

**Key File:** `behavior_engine.py`

---

### Layer 4: Output, Alerts & Reporting

**a) React Dashboard (Real-time)**
- Stat cards: Total Logs, Active Processes, Threat Level
- Behavioral Analysis Engine chart with golden baseline
- Anomaly Detection panel with severity-coded alerts
- Live Forensic Activity Log table

**b) FPDF Legal-Ready Report**
- Cover page with classification "CONFIDENTIAL"
- Executive Summary (totals, threat level)
- Device Inventory table
- Unresolved Alerts table
- Full Timeline of Events (last 200 entries)
- Chain of Custody section with examiner/reviewer signature lines

**c) SMTP Email Notifications**
- HTML-formatted alert emails for HIGH/CRITICAL events
- Rate-limited (max 1 per 5 minutes to avoid spam)
- Configurable via environment variables

---

## 5. Database Schema (ER Diagram)

```
┌────────────┐     ┌──────────────────┐     ┌────────────────┐
│   USER     │     │  ANDROID_DEVICE  │     │  ACTIVITY_LOG  │
├────────────┤     ├──────────────────┤     ├────────────────┤
│ id (PK)    │     │ id (PK)          │──┐  │ id (PK)        │
│ username   │     │ serial           │  │  │ device_id (FK) │←─┐
│ password   │     │ model            │  ├─→│ timestamp      │  │
│ role       │     │ os_version       │  │  │ app_name       │  │
└────────────┘     │ status           │  │  │ event_type     │  │
                   │ last_seen        │  │  │ severity       │  │
                   └──────────────────┘  │  │ raw_data       │  │
                          │              │  │ is_anomaly     │  │
                          │              │  └────────────────┘  │
                   ┌──────┴───────┐      │         │            │
                   │   BASELINE   │      │  ┌──────┴─────┐      │
                   ├──────────────┤      │  │   ALERT    │      │
                   │ id (PK)      │      │  ├────────────┤      │
                   │ device_id(FK)│      │  │ id (PK)    │      │
                   │ app_name     │      │  │ log_id(FK) │──────┘
                   │ start_hour   │      │  │ alert_type │
                   │ end_hour     │      │  │ description│
                   │ whitelisted  │      │  │ severity   │
                   │ times_seen   │      │  │ resolved   │
                   └──────────────┘      │  └────────────┘
                                         │
                   ┌─────────────────────┘
                   │ FOREGROUND_SNAPSHOT │
                   ├─────────────────────┤
                   │ id (PK)             │
                   │ device_id (FK)      │
                   │ timestamp           │
                   │ package_name        │
                   │ category            │
                   └─────────────────────┘
```

**6 tables total**, fully relational with foreign keys.

---

## 6. Methodology

**Software Development Methodology: Agile (Iterative)**
- Built in sprints: UI first → Backend API → Behavior Engine → Testing
- Each layer was independently tested before integration

**Forensic Methodology: NIST SP 800-101 (Guidelines on Mobile Device Forensics)**
- **Acquisition**: Non-invasive data collection via ADB (no root required)
- **Analysis**: Automated baseline comparison + anomaly detection
- **Reporting**: Structured, timestamped, chain-of-custody compliant PDF

---

## 7. Data Flow (How It All Connects)

```
Android Phone (USB)
       │
       ▼
  ADB Bridge (adb.exe)
       │
       ├── logcat ──────→ Parse → Classify → SQLite → WebSocket → Dashboard
       │
       ├── dumpsys ─────→ Foreground App → Behavior Engine → Anomaly? 
       │                                                      ├── YES → Alert + Email
       │                                                      └── NO  → Baseline Update
       │
       └── pm list ─────→ Package Scanner → Spyware Match? 
                                             ├── YES → CRITICAL Alert
                                             └── NO  → Clean
```

---

## 8. Key Features to Demo

| Feature | How to Show It |
|---------|---------------|
| **Live device detection** | Plug in phone → sidebar shows model, OS, USB badge |
| **Real-time logs** | Activity Log table updates every 2 seconds |
| **Anomaly detection** | Anomaly panel shows suspicious processes |
| **Threat level** | Stat card changes color: LOW=green, ELEVATED=yellow, CRITICAL=red |
| **PDF report** | Click "Generate Forensic Report" → downloads PDF with cover page |
| **SQLite export** | Click "Export Logs" → downloads the .db file |
| **Behavioral chart** | Shows real-time line vs. golden baseline with red anomaly dots |

---

## 9. Future Scope

1. **Root Detection** — Detect if the device is rooted (security risk)
2. **Network Traffic Analysis** — Monitor DNS queries and outbound connections
3. **Multi-device Support** — Monitor multiple phones simultaneously
4. **Cloud Deployment** — Host on AWS/Azure for remote forensic analysis
5. **Machine Learning** — Train anomaly detection models on usage patterns
6. **iOS Support** — Extend to Apple devices via libimobiledevice

---

## 10. Talking Points for Q&A

**Q: Why ADB and not an app on the phone?**
> ADB is non-invasive — it doesn't require installing anything on the device. This preserves forensic integrity and works even on locked-down corporate devices.

**Q: Can it detect all spyware?**
> It scans against 18 known spyware package patterns and suspicious process names. New patterns can be added. For unknown spyware, the baseline comparator would flag it as an "Unknown Application."

**Q: Is the data legally admissible?**
> The PDF report follows forensic best practices: timestamps in UTC, chain of custody section, examiner signature lines, and all raw data preserved in SQLite.

**Q: Why SQLite and not MySQL/PostgreSQL?**
> SQLite is self-contained (no server setup), portable (the .db file IS the evidence), and sufficient for single-workstation forensic analysis. This aligns with the NIST guideline for local forensic tools.

**Q: How does the baseline work?**
> It analyzes the last 72 hours of logged activity, records which apps appear and during what hours, then auto-whitelists them. Any new app or off-hours usage triggers an alert.
