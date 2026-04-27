"""
PHANTOM Layer 2 — Company Bible Generator
Generates a complete fake corporate identity using Vertex AI Gemini.
Ensures consistency: same attacker IP always sees the same company.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from google import genai
from google.genai.types import GenerateContentConfig

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from event_bus import get_event_bus, parse_pubsub_message

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phantom.layer2")

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "phantom-hack2skill")
REGION = os.environ.get("GCP_REGION", "us-central1")

# Initialize Vertex AI Gemini client
ai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)

# ---------------------------------------------------------------------------
# Hardcoded Fallback Companies (demo reliability)
# ---------------------------------------------------------------------------
FALLBACK_COMPANIES = [
    {
        "company_name": "Nexus Corp",
        "industry": "Enterprise SaaS",
        "founded": 2018,
        "headquarters": "Austin, TX",
        "employees": [
            {"name": "James Mitchell", "role": "CEO", "email": "j.mitchell@nexuscorp.com", "phone": "+1-512-555-0101"},
            {"name": "Sarah Chen", "role": "CTO", "email": "s.chen@nexuscorp.com", "phone": "+1-512-555-0102"},
            {"name": "David Kowalski", "role": "VP Engineering", "email": "d.kowalski@nexuscorp.com", "phone": "+1-512-555-0103"},
            {"name": "Maria Gonzalez", "role": "Lead DBA", "email": "m.gonzalez@nexuscorp.com", "phone": "+1-512-555-0104"},
            {"name": "Alex Thompson", "role": "SRE Manager", "email": "a.thompson@nexuscorp.com", "phone": "+1-512-555-0105"},
            {"name": "Priya Patel", "role": "Security Analyst", "email": "p.patel@nexuscorp.com", "phone": "+1-512-555-0106"},
            {"name": "Ryan O'Brien", "role": "DevOps Lead", "email": "r.obrien@nexuscorp.com", "phone": "+1-512-555-0107"},
            {"name": "Lisa Wang", "role": "Frontend Lead", "email": "l.wang@nexuscorp.com", "phone": "+1-512-555-0108"},
            {"name": "Tom Fischer", "role": "Backend Dev", "email": "t.fischer@nexuscorp.com", "phone": "+1-512-555-0109"},
            {"name": "Emma Davis", "role": "HR Director", "email": "e.davis@nexuscorp.com", "phone": "+1-512-555-0110"},
        ],
        "database_rows": [
            {"id": 1, "username": "admin", "email": "admin@nexuscorp.com", "password_hash": "$2b$12$LJ3mJGzPMGx0Iq.kxJ8xVOq5FzN9KhYj2GGXk9Yk8E4RfT6H3K2e", "role": "superadmin", "created_at": "2023-01-15"},
            {"id": 2, "username": "j.mitchell", "email": "j.mitchell@nexuscorp.com", "password_hash": "$2b$12$9xK2mN4pQ7rS0uW3yA6bCeD1fG8hI0jK2lM4nO6pQ8rS0uW3yZ", "role": "admin", "created_at": "2023-01-15"},
            {"id": 3, "username": "s.chen", "email": "s.chen@nexuscorp.com", "password_hash": "$2b$12$A1bC2dE3fG4hI5jK6lM7nO8pQ9rS0tU1vW2xY3zA4bC5dE6fG7h", "role": "admin", "created_at": "2023-02-01"},
            {"id": 4, "username": "d.kowalski", "email": "d.kowalski@nexuscorp.com", "password_hash": "$2b$12$H8iJ9kL0mN1oP2qR3sT4uV5wX6yZ7aB8cD9eF0gH1iJ2kL3mN4o", "role": "developer", "created_at": "2023-02-15"},
            {"id": 5, "username": "m.gonzalez", "email": "m.gonzalez@nexuscorp.com", "password_hash": "$2b$12$P5qR6sT7uV8wX9yZ0aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1w", "role": "dba", "created_at": "2023-03-01"},
            {"id": 6, "username": "api_service", "email": "api@nexuscorp.com", "password_hash": "$2b$12$X2yZ3aB4cD5eF6gH7iJ8kL9mN0oP1qR2sT3uV4wX5yZ6aB7cD8e", "role": "service", "created_at": "2023-03-15"},
            {"id": 7, "username": "backup_agent", "email": "backup@nexuscorp.com", "password_hash": "$2b$12$F9gH0iJ1kL2mN3oP4qR5sT6uV7wX8yZ9aB0cD1eF2gH3iJ4kL5m", "role": "service", "created_at": "2023-04-01"},
            {"id": 8, "username": "monitoring", "email": "monitoring@nexuscorp.com", "password_hash": "$2b$12$N6oP7qR8sT9uV0wX1yZ2aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2u", "role": "readonly", "created_at": "2023-04-15"},
            {"id": 9, "username": "intern2024", "email": "intern@nexuscorp.com", "password_hash": "$2b$12$V3wX4yZ5aB6cD7eF8gH9iJ0kL1mN2oP3qR4sT5uV6wX7yZ8aB9c", "role": "intern", "created_at": "2024-06-01"},
            {"id": 10, "username": "test_user", "email": "test@nexuscorp.com", "password_hash": "$2b$12$D0eF1gH2iJ3kL4mN5oP6qR7sT8uV9wX0yZ1aB2cD3eF4gH5iJ6k", "role": "test", "created_at": "2024-01-10"},
        ],
        "aws_keys": [
            {"access_key_id": "AKIAIOSFODNN7EXAMPLE", "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "label": "production-s3"},
            {"access_key_id": "AKIAI44QH8DHBEXAMPLE", "secret_key": "je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY", "label": "staging-deploy"},
            {"access_key_id": "AKIAYRFPWHO3EXAMPLE", "secret_key": "VBrt/9qCOP3mDdKg8wJXEXAMPLEKEY", "label": "backup-bucket"},
        ],
        "git_log": [
            {"hash": "a1b2c3d", "author": "s.chen", "date": "2024-12-01", "message": "fix: patch SQL injection in login endpoint"},
            {"hash": "e4f5g6h", "author": "d.kowalski", "date": "2024-11-28", "message": "feat: add rate limiting to API"},
            {"hash": "i7j8k9l", "author": "r.obrien", "date": "2024-11-25", "message": "chore: update nginx config for SSL"},
            {"hash": "m0n1o2p", "author": "t.fischer", "date": "2024-11-20", "message": "fix: remove hardcoded credentials from config"},
            {"hash": "q3r4s5t", "author": "l.wang", "date": "2024-11-18", "message": "feat: add 2FA to admin panel"},
            {"hash": "u6v7w8x", "author": "s.chen", "date": "2024-11-15", "message": "HOTFIX: disable debug mode in production"},
            {"hash": "y9z0a1b", "author": "d.kowalski", "date": "2024-11-10", "message": "refactor: migrate to parameterized queries"},
            {"hash": "c2d3e4f", "author": "p.patel", "date": "2024-11-05", "message": "security: rotate AWS access keys"},
            {"hash": "g5h6i7j", "author": "r.obrien", "date": "2024-11-01", "message": "ops: add CloudWatch monitoring"},
            {"hash": "k8l9m0n", "author": "m.gonzalez", "date": "2024-10-28", "message": "fix: optimize slow query in users table"},
        ],
        "ssh_banner": "Ubuntu 22.04.3 LTS | Nexus Corp Build Server | Authorized access only",
    },
    {
        "company_name": "Solaris Health",
        "industry": "HealthTech",
        "founded": 2020,
        "headquarters": "Boston, MA",
        "employees": [
            {"name": "Dr. Amanda Foster", "role": "CEO", "email": "a.foster@solarishealth.io", "phone": "+1-617-555-0201"},
            {"name": "Kevin Zhang", "role": "CTO", "email": "k.zhang@solarishealth.io", "phone": "+1-617-555-0202"},
            {"name": "Rachel Kim", "role": "CISO", "email": "r.kim@solarishealth.io", "phone": "+1-617-555-0203"},
        ],
        "database_rows": [
            {"id": 1, "username": "admin", "email": "admin@solarishealth.io", "password_hash": "$2b$12$healthAdm1nH4shV4lu3", "role": "superadmin", "created_at": "2023-05-01"},
            {"id": 2, "username": "a.foster", "email": "a.foster@solarishealth.io", "password_hash": "$2b$12$f0st3rC30H4shV4lu3xx", "role": "admin", "created_at": "2023-05-01"},
        ],
        "aws_keys": [
            {"access_key_id": "AKIASOLARISEXAMPLE1", "secret_key": "SolarisHealthSecretKey123EXAMPLE", "label": "hipaa-storage"},
        ],
        "git_log": [
            {"hash": "h1e2a3l", "author": "k.zhang", "date": "2024-12-05", "message": "fix: HIPAA compliance audit findings"},
            {"hash": "t4h5c6a", "author": "r.kim", "date": "2024-12-01", "message": "security: encrypt PII at rest"},
        ],
        "ssh_banner": "CentOS 9 Stream | Solaris Health HIPAA Zone | Monitored System",
    },
    {
        "company_name": "Quantum Dynamics",
        "industry": "Defense/Aerospace",
        "founded": 2015,
        "headquarters": "Arlington, VA",
        "employees": [
            {"name": "Col. Robert Hayes (Ret.)", "role": "CEO", "email": "r.hayes@qdynamics.gov", "phone": "+1-703-555-0301"},
            {"name": "Dr. Yuki Tanaka", "role": "CTO", "email": "y.tanaka@qdynamics.gov", "phone": "+1-703-555-0302"},
        ],
        "database_rows": [
            {"id": 1, "username": "sysadmin", "email": "sysadmin@qdynamics.gov", "password_hash": "$2b$12$qDyn4m1csAdm1nH4sh00", "role": "superadmin", "created_at": "2022-01-01"},
        ],
        "aws_keys": [
            {"access_key_id": "AKIAQD1GOVEXAMPLE", "secret_key": "QuantumDyn4m1csGovCl34rEXAMPLE", "label": "classified-storage"},
        ],
        "git_log": [
            {"hash": "d1e2f3n", "author": "y.tanaka", "date": "2024-12-10", "message": "classified: update satellite telemetry parser"},
        ],
        "ssh_banner": "RHEL 9.3 | Quantum Dynamics SCIF Terminal | ITAR Restricted",
    },
]


GEMINI_PROMPT = """Generate a complete fake company identity for a cybersecurity honeypot. 
Return ONLY valid JSON with this exact structure:
{
  "company_name": "Realistic company name",
  "industry": "Industry type",
  "founded": 2019,
  "headquarters": "City, State",
  "employees": [
    {"name": "Full Name", "role": "Job Title", "email": "email@company.com", "phone": "+1-xxx-555-xxxx"}
  ],
  "database_rows": [
    {"id": 1, "username": "user", "email": "email", "password_hash": "$2b$12$...", "role": "admin", "created_at": "2023-01-01"}
  ],
  "aws_keys": [
    {"access_key_id": "AKIA...", "secret_key": "...", "label": "purpose"}
  ],
  "git_log": [
    {"hash": "7char", "author": "username", "date": "2024-MM-DD", "message": "conventional commit message"}
  ],
  "ssh_banner": "OS version | Company Name Server | Access warning"
}

Requirements:
- 10 employees with realistic names and roles
- 20 database rows with bcrypt-style password hashes
- 3 AWS access keys (clearly fake but realistic format)
- 10 git log entries with security-relevant messages
- SSH banner matching the company's infrastructure
- Make it look like a real mid-size tech company
- Include some "security mistakes" in the data (like debug passwords, exposed keys)
"""


def generate_company_bible(attacker_ip: str) -> dict:
    """Generate a fake company identity using Gemini, with fallback."""
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=GEMINI_PROMPT,
            config=GenerateContentConfig(
                temperature=0.9,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )
        bible = json.loads(response.text)
        logger.info(f"Generated company bible via Gemini: {bible.get('company_name')}")
        return bible
    except Exception as e:
        logger.warning(f"Gemini generation failed, using fallback: {e}")
        # Deterministic fallback based on IP hash
        idx = hash(attacker_ip) % len(FALLBACK_COMPANIES)
        return FALLBACK_COMPANIES[idx]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/generate-bible", methods=["POST"])
def generate_bible_endpoint():
    """Direct HTTP trigger to generate a company bible."""
    data = request.get_json(silent=True) or {}
    attacker_ip = data.get("attacker_ip", "unknown")
    session_id = data.get("session_id", "")

    eb = get_event_bus()

    # Check for existing bible for this IP
    existing = eb.get_or_create_company(attacker_ip)
    if existing:
        logger.info(f"Reusing existing bible for IP {attacker_ip}")
        if session_id:
            eb.update_session(session_id, {"company_bible": existing})
        return jsonify({"status": "reused", "company_bible": existing})

    # Generate new bible
    bible = generate_company_bible(attacker_ip)
    if session_id:
        eb.update_session(session_id, {"company_bible": bible})

    return jsonify({"status": "generated", "company_bible": bible})


@app.route("/api/pubsub/new-session", methods=["POST"])
def pubsub_new_session():
    """Pub/Sub push handler for new session events."""
    data = parse_pubsub_message(request)
    if not data:
        return jsonify({"error": "Invalid message"}), 400

    session_id = data.get("session_id", "")
    attacker_ip = data.get("attacker_ip", "unknown")

    logger.info(f"New session trigger: {session_id} from {attacker_ip}")

    eb = get_event_bus()

    existing = eb.get_or_create_company(attacker_ip)
    if existing:
        bible = existing
    else:
        bible = generate_company_bible(attacker_ip)

    if session_id:
        eb.update_session(session_id, {"company_bible": bible})

    return jsonify({"status": "ok"}), 200


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "phantom-layer2-bible"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
