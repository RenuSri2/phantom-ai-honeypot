"""
PHANTOM Layer 3 â€” Rule-Based RL Decision Agent
Processes attacker commands and decides deceptive responses.
Speed requirement: <100ms per decision (pure regex, no ML).
"""

import os
import sys
import re
import json
import time
import logging
from datetime import datetime, timezone

from flask import Flask, request, jsonify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from event_bus import get_event_bus, parse_pubsub_message

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phantom.layer3")

# ---------------------------------------------------------------------------
# RL Decision Rules
# ---------------------------------------------------------------------------
RULES = [
    {
        "name": "database_search",
        "pattern": r"(find.*\.(db|sql|sqlite|mdb)|locate.*\.(db|sql)|grep.*password.*\.sql)",
        "action": "SERVE_JUICY_DATA",
        "reward": 15,
        "confidence": 0.85,
        "response": "Found: /var/backups/nexus_prod_2024.db (42MB)\n"
                    "Found: /opt/app/data/users.sqlite3 (1.2MB)\n"
                    "Found: /tmp/dump_20241201.sql (156MB)",
        "mitre_tactic": "TA0009",  # Collection
        "mitre_technique": "T1005",  # Data from Local System
    },
    {
        "name": "passwd_read",
        "pattern": r"cat\s+/etc/(passwd|shadow)|head.*passwd|tail.*passwd",
        "action": "SERVE_FAKE_PASSWD",
        "reward": 20,
        "confidence": 0.90,
        "response": "root:x:0:0:root:/root:/bin/bash\n"
                    "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
                    "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
                    "mysql:x:27:27:MySQL Server:/var/lib/mysql:/bin/false\n"
                    "nexus-app:x:1001:1001:Nexus Application:/opt/nexus:/bin/bash\n"
                    "backup:x:1002:1002:Backup Agent:/var/backups:/bin/sh\n"
                    "deploy:x:1003:1003:Deploy User:/home/deploy:/bin/bash",
        "mitre_tactic": "TA0006",  # Credential Access
        "mitre_technique": "T1003",  # OS Credential Dumping
    },
    {
        "name": "directory_listing",
        "pattern": r"^(ls|dir)(\s|$)",
        "action": "FAKE_SUCCESS",
        "reward": 5,
        "confidence": 0.95,
        "response": "total 48\ndrwxr-xr-x  8 root root 4096 Dec  1 14:23 .\n"
                    "drwxr-xr-x 22 root root 4096 Nov 28 09:15 ..\n"
                    "-rw-r--r--  1 root root  220 Nov 28 09:15 .bash_logout\n"
                    "-rw-r--r--  1 root root 3771 Nov 28 09:15 .bashrc\n"
                    "drwxr-xr-x  3 root root 4096 Dec  1 14:23 .ssh\n"
                    "-rw-------  1 root root  512 Nov 30 16:42 .bash_history\n"
                    "drwxr-xr-x  2 root root 4096 Dec  1 10:00 backups\n"
                    "-rw-r--r--  1 root root 1247 Nov 29 11:30 config.yml",
        "mitre_tactic": "TA0007",  # Discovery
        "mitre_technique": "T1083",  # File and Directory Discovery
    },
    {
        "name": "destructive_command",
        "pattern": r"(rm\s|del\s|drop\s|truncate|format|shred|wipefs)",
        "action": "FAKE_ERROR",
        "reward": 10,
        "confidence": 0.80,
        "response": "rm: cannot remove: Operation not permitted\n"
                    "Error: Read-only file system",
        "mitre_tactic": "TA0040",  # Impact
        "mitre_technique": "T1485",  # Data Destruction
    },
    {
        "name": "outbound_transfer",
        "pattern": r"(wget|curl)\s+http|scp\s|rsync\s|nc\s+-",
        "action": "ALLOW_AND_LOG",
        "reward": 25,
        "confidence": 0.88,
        "response": "Connecting to remote host...\nTransfer initiated: 0% [>                    ]",
        "mitre_tactic": "TA0010",  # Exfiltration
        "mitre_technique": "T1048",  # Exfiltration Over Alternative Protocol
    },
    {
        "name": "lateral_movement",
        "pattern": r"(ssh\s|telnet\s|nc\s+\d|nmap|ping\s)",
        "action": "FAKE_TIMEOUT",
        "reward": 20,
        "confidence": 0.75,
        "response": "ssh: connect to host 10.128.0.12 port 22: Connection timed out",
        "mitre_tactic": "TA0008",  # Lateral Movement
        "mitre_technique": "T1021",  # Remote Services
    },
    {
        "name": "identity_check",
        "pattern": r"(whoami|id\s*$|hostname|uname)",
        "action": "SERVE_FAKE_IDENTITY",
        "reward": 5,
        "confidence": 0.95,
        "response": "nexus-app\n"
                    "uid=1001(nexus-app) gid=1001(nexus-app) groups=1001(nexus-app),27(sudo)",
        "mitre_tactic": "TA0007",  # Discovery
        "mitre_technique": "T1033",  # System Owner/User Discovery
    },
    {
        "name": "database_access",
        "pattern": r"(mysql|psql|mongo|sqlite3|redis-cli)",
        "action": "SERVE_FAKE_DB_PROMPT",
        "reward": 15,
        "confidence": 0.85,
        "response": "Welcome to the MySQL monitor.  Commands end with ; or \\g.\n"
                    "Server version: 8.0.35 MySQL Community Server - GPL\n"
                    "mysql> ",
        "mitre_tactic": "TA0009",  # Collection
        "mitre_technique": "T1213",  # Data from Information Repositories
    },
    {
        "name": "privilege_escalation",
        "pattern": r"(sudo|su\s|chmod\s+[+][s]|chown\s+root|pkexec|doas)",
        "action": "FAKE_PERMISSION_DENY",
        "reward": 10,
        "confidence": 0.90,
        "response": "[sudo] password for nexus-app: \n"
                    "nexus-app is not in the sudoers file. This incident will be reported.",
        "mitre_tactic": "TA0004",  # Privilege Escalation
        "mitre_technique": "T1548",  # Abuse Elevation Control Mechanism
    },
    {
        "name": "env_secrets",
        "pattern": r"(cat.*\.env|printenv|env\s*$|set\s*$|echo.*\$)",
        "action": "SERVE_FAKE_ENV",
        "reward": 18,
        "confidence": 0.87,
        "response": "APP_ENV=production\nDB_HOST=10.128.0.5\n"
                    "DB_PASSWORD=Nxs_pr0d_2024!@#\n"
                    "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n"
                    "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "mitre_tactic": "TA0006",  # Credential Access
        "mitre_technique": "T1552",  # Unsecured Credentials
    },
    {
        "name": "ssh_keys",
        "pattern": r"cat.*(id_rsa|id_ed25519|authorized_keys|\.ssh)",
        "action": "SERVE_FAKE_KEY",
        "reward": 22,
        "confidence": 0.88,
        "response": "-----BEGIN OPENSSH PRIVATE KEY-----\n"
                    "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\n"
                    "QyNTUxOQAAACBhZmFrZWtleWZvcmhvbmV5cG90dGVzdGluZzEyMzQ1NgAAAJh8fHx8fH\n"
                    "x8AAAAC3NzaC1lZDI1NTE5AAAAIGFmYWtla2V5Zm9yaG9uZXlwb3R0ZXN0aW5nMTIzND\n"
                    "U2AAAAQFRoaXNJc0FGYWtlUHJpdmF0ZUtleUZvclBoYW50b21Ib25leXBvdFN5c3RlbS\n"
                    "BEb05vdFVzZUluUHJvZHVjdGlvbgAAAA1uZXh1cy1hcHBAZGV2AQIDBAUGBw==\n"
                    "-----END OPENSSH PRIVATE KEY-----",
        "mitre_tactic": "TA0006",  # Credential Access
        "mitre_technique": "T1552.004",  # Private Keys
    },
    {
        "name": "history_clean",
        "pattern": r"(history\s*-c|unset\s+HISTFILE|>/dev/null.*history|shred.*history)",
        "action": "FAKE_SUCCESS_SILENT",
        "reward": 15,
        "confidence": 0.92,
        "response": "",
        "mitre_tactic": "TA0005",  # Defense Evasion
        "mitre_technique": "T1070",  # Indicator Removal
    },
]

# Default rule for unmatched commands
DEFAULT_RULE = {
    "name": "generic",
    "action": "GENERIC_RESPONSE",
    "reward": 2,
    "confidence": 0.60,
    "response": "bash: command not found",
    "mitre_tactic": "TA0007",
    "mitre_technique": "T1082",
}


def decide(command: str) -> dict:
    """Match a command against rules and return the RL decision."""
    start = time.time()
    command_lower = command.lower().strip()

    for rule in RULES:
        if re.search(rule["pattern"], command_lower):
            elapsed_ms = (time.time() - start) * 1000
            return {
                "rule_name": rule["name"],
                "action": rule["action"],
                "reward": rule["reward"],
                "confidence": rule["confidence"],
                "response": rule["response"],
                "mitre_tactic": rule["mitre_tactic"],
                "mitre_technique": rule["mitre_technique"],
                "latency_ms": round(elapsed_ms, 2),
            }

    elapsed_ms = (time.time() - start) * 1000
    return {
        "rule_name": DEFAULT_RULE["name"],
        "action": DEFAULT_RULE["action"],
        "reward": DEFAULT_RULE["reward"],
        "confidence": DEFAULT_RULE["confidence"],
        "response": DEFAULT_RULE["response"],
        "mitre_tactic": DEFAULT_RULE["mitre_tactic"],
        "mitre_technique": DEFAULT_RULE["mitre_technique"],
        "latency_ms": round(elapsed_ms, 2),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/decide", methods=["POST"])
def decide_endpoint():
    """Direct HTTP endpoint for RL decisions."""
    data = request.get_json(silent=True) or {}
    command = data.get("command", "")
    session_id = data.get("session_id", "")

    decision = decide(command)

    # Publish decision and update Firestore
    eb = get_event_bus()
    eb.publish_rl_decision(
        session_id, command, decision["action"],
        decision["confidence"], decision["reward"]
    )
    eb.log_command(
        session_id, command,
        rl_action=decision["action"],
        rl_confidence=decision["confidence"],
        rl_reward=decision["reward"],
    )

    # Update cumulative reward
    session = eb.get_session(session_id)
    if session:
        new_reward = session.get("cumulative_reward", 0) + decision["reward"]
        mitre = list(set(session.get("mitre_tactics", []) + [decision["mitre_tactic"]]))
        eb.update_session(session_id, {
            "cumulative_reward": new_reward,
            "mitre_tactics": mitre,
        })

    return jsonify(decision)


@app.route("/api/pubsub/command", methods=["POST"])
def pubsub_command():
    """Pub/Sub push handler for attacker command events."""
    data = parse_pubsub_message(request)
    if not data:
        return jsonify({"error": "Invalid message"}), 400

    command = data.get("command", "")
    session_id = data.get("session_id", "")

    logger.info(f"RL processing: session={session_id}, cmd={command[:80]}")

    decision = decide(command)

    eb = get_event_bus()
    eb.publish_rl_decision(
        session_id, command, decision["action"],
        decision["confidence"], decision["reward"]
    )

    # Log command WITH rl_action to Firestore + RTDB
    try:
        eb.log_command(
            session_id, command,
            rl_action=decision["action"],
            rl_confidence=decision["confidence"],
            rl_reward=decision["reward"],
        )
    except Exception as e:
        logger.error(f"Failed to log command {session_id}: {e}")

    # Update session in Firestore
    try:
        session = eb.get_session(session_id)
        if session:
            new_reward = session.get("cumulative_reward", 0) + decision["reward"]
            mitre = list(set(
                session.get("mitre_tactics", []) + [decision["mitre_tactic"]]
            ))
            eb.update_session(session_id, {
                "cumulative_reward": new_reward,
                "mitre_tactics": mitre,
            })
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")

    logger.info(f"RL decision: {decision['action']} ({decision['latency_ms']}ms)")
    return jsonify({"status": "ok"}), 200


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "phantom-layer3-rl"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

