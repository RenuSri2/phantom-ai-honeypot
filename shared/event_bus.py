"""
PHANTOM — Central Event Bus
Shared module for Pub/Sub messaging + Firestore session management.
All 5 layers import this module.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone

from google.cloud import pubsub_v1
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, db as rtdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phantom.event_bus")

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "phantom-hack2skill")
REGION = os.environ.get("GCP_REGION", "us-central1")

TOPIC_ATTACKER_COMMANDS   = "attacker-commands"
TOPIC_NEW_SESSION         = "new-session"
TOPIC_RL_DECISIONS        = "rl-decisions"
TOPIC_ATTACKER_DISCONNECT = "attacker-disconnect"
TOPIC_SIMULATION_EVENTS   = "simulation-events"


class PhantomEventBus:

    def __init__(self):
        self.project_id = PROJECT_ID
        self.publisher  = pubsub_v1.PublisherClient()
        self.db         = firestore.Client(project=PROJECT_ID)
        logger.info(f"PhantomEventBus initialized for project: {PROJECT_ID}")

    def _topic_path(self, topic_name):
        return self.publisher.topic_path(self.project_id, topic_name)

    def _get_rtdb(self):
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={
                "databaseURL": f"https://{self.project_id}-default-rtdb.firebaseio.com"
            })
        return rtdb

    def _mirror_session_to_rtdb(self, session_id, data):
        """Mirror session fields to RTDB so frontend can read them live."""
        try:
            rt = self._get_rtdb()
            # Filter out non-serializable Firestore sentinels
            clean = {}
            for k, v in data.items():
                if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                    clean[k] = v
            if clean:
                rt.reference(f"sessions/{session_id}/info").update(clean)
        except Exception as e:
            logger.warning(f"RTDB session mirror failed: {e}")

    # ------------------------------------------------------------------
    # Pub/Sub Publishing
    # ------------------------------------------------------------------

    def publish_event(self, topic, data, session_id=None, is_simulated=False):
        payload = {
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "session_id":   session_id,
            "is_simulated": is_simulated,
            **data,
        }
        message_bytes = json.dumps(payload).encode("utf-8")
        attrs = {"session_id": session_id or "", "is_simulated": str(is_simulated)}
        future = self.publisher.publish(self._topic_path(topic), message_bytes, **attrs)
        msg_id = future.result(timeout=10)
        logger.info(f"Published to {topic}: msg_id={msg_id}, session={session_id}")
        return msg_id

    def publish_command(self, session_id, command, source="real", attacker_ip=""):
        return self.publish_event(
            TOPIC_ATTACKER_COMMANDS,
            {"command": command, "source": source, "attacker_ip": attacker_ip},
            session_id=session_id,
            is_simulated=(source == "simulated"),
        )

    def publish_new_session(self, session_id, attacker_ip, is_simulated=False):
        return self.publish_event(
            TOPIC_NEW_SESSION, {"attacker_ip": attacker_ip},
            session_id=session_id, is_simulated=is_simulated,
        )

    def publish_rl_decision(self, session_id, command, action, confidence, reward):
        return self.publish_event(
            TOPIC_RL_DECISIONS,
            {"command": command, "action": action, "confidence": confidence, "reward": reward},
            session_id=session_id,
        )

    def publish_disconnect(self, session_id):
        return self.publish_event(
            TOPIC_ATTACKER_DISCONNECT, {"reason": "disconnect"}, session_id=session_id,
        )

    # ------------------------------------------------------------------
    # Firestore + RTDB Session Management
    # ------------------------------------------------------------------

    def create_session(self, attacker_ip, is_simulated=False):
        session_id = str(uuid.uuid4())[:12]
        data = {
            "session_id":        session_id,
            "attacker_ip":       attacker_ip,
            "is_simulated":      is_simulated,
            "session_type":      "SIMULATED" if is_simulated else "REAL",
            "start_time":        firestore.SERVER_TIMESTAMP,
            "end_time":          None,
            "threat_score":      0,
            "skill_level":       "unknown",
            "intent":            "unknown",
            "company_bible":     {},
            "mitre_tactics":     [],
            "geo":               {},
            "status":            "active",
            "command_count":     0,
            "cumulative_reward": 0,
        }
        self.db.collection("sessions").document(session_id).set(data)

        # Mirror to RTDB immediately
        self._mirror_session_to_rtdb(session_id, {
            "session_id":    session_id,
            "attacker_ip":   attacker_ip,
            "session_type":  "SIMULATED" if is_simulated else "REAL",
            "threat_score":  0,
            "skill_level":   "unknown",
            "intent":        "unknown",
            "status":        "active",
            "command_count": 0,
            "cumulative_reward": 0,
        })

        logger.info(f"Session created: {session_id} for IP {attacker_ip}")
        return session_id

    def get_session(self, session_id):
        doc = self.db.collection("sessions").document(session_id).get()
        return doc.to_dict() if doc.exists else {}

    def update_session(self, session_id, data):
        self.db.collection("sessions").document(session_id).update(data)
        self._mirror_session_to_rtdb(session_id, data)
        logger.info(f"Session updated: {session_id}, fields={list(data.keys())}")

    def end_session(self, session_id):
        self.update_session(session_id, {"end_time": None, "status": "completed"})

    def log_command(self, session_id, command, source="real",
                    rl_action="", rl_confidence=0, rl_reward=0):
        cmd_ref = (
            self.db.collection("sessions").document(session_id)
            .collection("commands").document()
        )
        cmd_ref.set({
            "timestamp":     firestore.SERVER_TIMESTAMP,
            "raw_command":   command,
            "source":        source,
            "rl_action":     rl_action,
            "rl_confidence": rl_confidence,
            "rl_reward":     rl_reward,
        })

        self.db.collection("sessions").document(session_id).update({
            "command_count": firestore.Increment(1),
        })

        # Write command to RTDB
        try:
            rt = self._get_rtdb()
            rt.reference(f"sessions/{session_id}/commands").push({
                "timestamp":     int(datetime.now(timezone.utc).timestamp() * 1000),
                "raw_command":   command,
                "source":        source,
                "rl_action":     rl_action,
                "rl_confidence": rl_confidence,
                "rl_reward":     rl_reward,
            })
            # Also update command count in RTDB
            existing = rt.reference(f"sessions/{session_id}/info/command_count").get()
            rt.reference(f"sessions/{session_id}/info/command_count").set((existing or 0) + 1)
        except Exception as e:
            logger.warning(f"RTDB write failed: {e}")

    def get_commands(self, session_id):
        cmds = (
            self.db.collection("sessions").document(session_id)
            .collection("commands").order_by("timestamp").stream()
        )
        return [c.to_dict() for c in cmds]

    def get_or_create_company(self, attacker_ip):
        sessions = (
            self.db.collection("sessions")
            .where("attacker_ip", "==", attacker_ip)
            .where("company_bible", "!=", {})
            .limit(1).stream()
        )
        for session in sessions:
            data = session.to_dict()
            if data.get("company_bible"):
                return data["company_bible"]
        return None

    def save_report_metadata(self, session_id, pdf_url, executive_summary="", mitre_mapping=None):
        self.db.collection("reports").document(session_id).set({
            "session_id":        session_id,
            "pdf_url":           pdf_url,
            "generated_at":      firestore.SERVER_TIMESTAMP,
            "executive_summary": executive_summary,
            "mitre_mapping":     mitre_mapping or [],
        })
        self.update_session(session_id, {"status": "report_generated", "pdf_url": pdf_url})


def parse_pubsub_message(request):
    envelope = request.get_json(silent=True)
    if not envelope:
        return {}
    message = envelope.get("message", {})
    if not message:
        return {}
    import base64
    data_bytes = base64.b64decode(message.get("data", ""))
    try:
        return json.loads(data_bytes)
    except json.JSONDecodeError:
        return {}


_bus_instance = None

def get_event_bus():
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = PhantomEventBus()
    return _bus_instance
