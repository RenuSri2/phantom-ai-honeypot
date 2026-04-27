"""
PHANTOM Layer 4 — Behavioral Analysis + Intent Classification
Processes RL decisions to classify attacker skill level and intent.
Uses Vertex AI Gemini for intent classification, rule-based skill assessment.
Runs async — never blocks the attacker.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from collections import Counter

from flask import Flask, request, jsonify
from google import genai
from google.genai.types import GenerateContentConfig

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from event_bus import get_event_bus, parse_pubsub_message

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phantom.layer4")

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "phantom-hack2skill")
REGION = os.environ.get("GCP_REGION", "us-central1")

ai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)

# ---------------------------------------------------------------------------
# Skill Level Assessment (Rule-Based Heuristics)
# ---------------------------------------------------------------------------
ADVANCED_PATTERNS = [
    "base64", "encoded", "obfusc", "\\x", "%00", "&&", "||",
    "$(", "`", "2>/dev/null", "/dev/null", "history -c",
    "unset HISTFILE", "shred", "pivot", "proxy", "tor",
    "nmap -sS", "nmap -sV", "-T0", "-T1",
]

INTERMEDIATE_PATTERNS = [
    "sudo", "su ", "chmod", "chown", "find / -perm",
    "grep -r", "pipe", "|", "xargs", "awk", "sed",
    "curl", "wget", "scp", "rsync",
]

SCRIPT_KIDDIE_PATTERNS = [
    "help", "ls", "dir", "whoami", "id", "pwd",
    "cat /etc/passwd", "uname -a",
]


def assess_skill_level(commands: list) -> dict:
    """Assess attacker skill level from command history."""
    if not commands:
        return {"level": "unknown", "score": 0, "indicators": []}

    cmd_texts = [c.get("raw_command", "").lower() for c in commands]
    all_text = " ".join(cmd_texts)
    unique_cmds = len(set(cmd_texts))
    total_cmds = len(cmd_texts)

    indicators = []
    advanced_count = 0
    intermediate_count = 0
    basic_count = 0

    for pattern in ADVANCED_PATTERNS:
        if pattern in all_text:
            advanced_count += 1
            indicators.append(f"Advanced: {pattern}")

    for pattern in INTERMEDIATE_PATTERNS:
        if pattern in all_text:
            intermediate_count += 1
            indicators.append(f"Intermediate: {pattern}")

    for pattern in SCRIPT_KIDDIE_PATTERNS:
        if pattern in all_text:
            basic_count += 1

    # Scoring: 0-33 = script kiddie, 34-66 = intermediate, 67-100 = APT
    diversity_score = min(30, (unique_cmds / max(total_cmds, 1)) * 30)
    adv_score = min(40, advanced_count * 10)
    int_score = min(20, intermediate_count * 5)
    speed_score = min(10, total_cmds / 3)

    total_score = int(diversity_score + adv_score + int_score + speed_score)
    total_score = min(100, total_score)

    if total_score >= 67:
        level = "APT"
    elif total_score >= 34:
        level = "intermediate"
    else:
        level = "script_kiddie"

    return {
        "level": level,
        "score": total_score,
        "indicators": indicators[:10],
        "unique_commands": unique_cmds,
        "total_commands": total_cmds,
    }


# ---------------------------------------------------------------------------
# Intent Classification (Gemini-Powered)
# ---------------------------------------------------------------------------
INTENT_PROMPT = """Analyze these commands from a cybersecurity honeypot attacker session.
Classify the PRIMARY intent as exactly one of:
- data_theft
- reconnaissance
- sabotage
- credential_harvesting
- lateral_movement

Also identify the top 3 tools/techniques being used.

Commands:
{commands}

Respond in JSON format only:
{{
  "intent": "primary_intent",
  "confidence": 0.85,
  "tools_detected": ["tool1", "tool2", "tool3"],
  "reasoning": "Brief explanation"
}}"""

# Track which sessions have been analyzed and at what command count
analysis_cache = {}


def classify_intent(commands: list) -> dict:
    """Classify attacker intent using Gemini."""
    cmd_texts = [c.get("raw_command", "") for c in commands[-15:]]
    prompt = INTENT_PROMPT.format(commands="\n".join(cmd_texts))

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=512,
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        logger.info(f"Intent classified: {result.get('intent')}")
        return result
    except Exception as e:
        logger.warning(f"Gemini intent classification failed: {e}")
        return classify_intent_fallback(commands)


def classify_intent_fallback(commands: list) -> dict:
    """Keyword-based fallback for intent classification."""
    cmd_texts = " ".join(c.get("raw_command", "").lower() for c in commands)

    scores = {
        "data_theft": 0,
        "reconnaissance": 0,
        "sabotage": 0,
        "credential_harvesting": 0,
        "lateral_movement": 0,
    }

    # Data theft indicators
    for kw in ["backup", "dump", "exfil", "tar ", "zip ", "scp ", "curl.*POST",
               "wget", ".db", ".sql", "SELECT", "mysqldump"]:
        if kw in cmd_texts:
            scores["data_theft"] += 3

    # Recon indicators
    for kw in ["ls", "dir", "find", "locate", "whoami", "id", "uname",
               "nmap", "scan", "enum", "GET /", "robots"]:
        if kw in cmd_texts:
            scores["reconnaissance"] += 2

    # Sabotage indicators
    for kw in ["rm ", "del ", "drop ", "truncate", "format", "shred",
               "dd if=/dev/zero", "mkfs", "wipefs"]:
        if kw in cmd_texts:
            scores["sabotage"] += 4

    # Credential harvesting
    for kw in ["passwd", "shadow", "credential", "password", "login",
               "hash", ".env", "aws_", "secret", "token", "id_rsa"]:
        if kw in cmd_texts:
            scores["credential_harvesting"] += 3

    # Lateral movement
    for kw in ["ssh ", "telnet", "rdp", "pivot", "proxy", "tunnel",
               "nc ", "ncat", "10.128", "internal"]:
        if kw in cmd_texts:
            scores["lateral_movement"] += 3

    intent = max(scores, key=scores.get)
    max_score = max(scores.values())
    confidence = min(0.95, max_score / 20)

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "tools_detected": [],
        "reasoning": "Keyword-based fallback classification",
    }


# ---------------------------------------------------------------------------
# Threat Score Calculation
# ---------------------------------------------------------------------------
def calculate_threat_score(session: dict, skill: dict, intent_data: dict) -> int:
    """Calculate composite threat score (0-100)."""
    weights = {
        "skill": 0.25,
        "intent_severity": 0.25,
        "command_volume": 0.20,
        "anomaly": 0.15,
        "time_factor": 0.15,
    }

    intent_severity = {
        "sabotage": 95, "data_theft": 85, "credential_harvesting": 75,
        "lateral_movement": 70, "reconnaissance": 40, "unknown": 20,
    }

    skill_score = skill.get("score", 0)
    intent_score = intent_severity.get(intent_data.get("intent", "unknown"), 20)
    cmd_count = session.get("command_count", 0)
    cmd_score = min(100, cmd_count * 5)
    anomaly_score = session.get("threat_score", 0)
    time_score = min(100, cmd_count * 3)  # Proxy for time in session

    total = (
        weights["skill"] * skill_score +
        weights["intent_severity"] * intent_score +
        weights["command_volume"] * cmd_score +
        weights["anomaly"] * anomaly_score +
        weights["time_factor"] * time_score
    )
    return int(min(100, max(0, total)))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/analyze", methods=["POST"])
def analyze_endpoint():
    """Direct HTTP trigger for behavioral analysis."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    eb = get_event_bus()
    session = eb.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    commands = eb.get_commands(session_id)

    # Skill assessment
    skill = assess_skill_level(commands)

    # Intent classification (batch every 5 commands)
    cache_key = session_id
    last_count = analysis_cache.get(cache_key, 0)
    cmd_count = len(commands)

    if cmd_count - last_count >= 5 or cmd_count <= 5:
        intent_data = classify_intent(commands)
        analysis_cache[cache_key] = cmd_count
    else:
        intent_data = {
            "intent": session.get("intent", "unknown"),
            "confidence": 0.5,
            "tools_detected": [],
            "reasoning": "Cached — waiting for more commands",
        }

    # Threat score
    threat_score = calculate_threat_score(session, skill, intent_data)

    # Update Firestore
    update = {
        "skill_level": skill["level"],
        "skill_score": skill["score"],
        "intent": intent_data["intent"],
        "intent_confidence": intent_data.get("confidence", 0),
        "tools_detected": intent_data.get("tools_detected", []),
        "threat_score": threat_score,
    }
    eb.update_session(session_id, update)

    return jsonify({
        "session_id": session_id,
        "skill": skill,
        "intent": intent_data,
        "threat_score": threat_score,
    })


@app.route("/api/pubsub/rl-decision", methods=["POST"])
def pubsub_rl_decision():
    """Pub/Sub push handler for RL decision events."""
    data = parse_pubsub_message(request)
    if not data:
        return jsonify({"error": "Invalid message"}), 400

    session_id = data.get("session_id", "")
    if not session_id:
        return jsonify({"status": "skipped", "reason": "no session_id"}), 200

    logger.info(f"Analysis triggered for session {session_id}")

    eb = get_event_bus()
    session = eb.get_session(session_id)
    if not session:
        return jsonify({"status": "skipped", "reason": "session not found"}), 200

    commands = eb.get_commands(session_id)
    cmd_count = len(commands)

    # Skill assessment (always fast)
    skill = assess_skill_level(commands)

    # Intent classification (batch every 5 commands to reduce API calls)
    cache_key = session_id
    last_count = analysis_cache.get(cache_key, 0)

    if cmd_count - last_count >= 5 or cmd_count <= 3:
        intent_data = classify_intent(commands)
        analysis_cache[cache_key] = cmd_count
    else:
        intent_data = {
            "intent": session.get("intent", "reconnaissance"),
            "confidence": 0.5,
            "tools_detected": session.get("tools_detected", []),
        }

    threat_score = calculate_threat_score(session, skill, intent_data)

    try:
        eb.update_session(session_id, {
            "skill_level": skill["level"],
            "skill_score": skill["score"],
            "intent": intent_data["intent"],
            "intent_confidence": intent_data.get("confidence", 0),
            "tools_detected": intent_data.get("tools_detected", []),
            "threat_score": threat_score,
        })
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")

    logger.info(f"Analysis complete: skill={skill['level']}, "
                f"intent={intent_data['intent']}, score={threat_score}")

    return jsonify({"status": "ok"}), 200


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "phantom-layer4-analysis"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
