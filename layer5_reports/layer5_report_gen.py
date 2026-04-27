"""
PHANTOM Layer 5 â€” Threat Intelligence Report Generator
Generates professional dark-themed PDF reports using ReportLab.
Triggered by Pub/Sub disconnect, timeout, or manual API call.
"""

import os
import sys
import json
import logging
import requests as http_requests
from datetime import datetime, timezone
from io import BytesIO

from flask import Flask, request, jsonify, send_file
from google.cloud import storage
from google import genai
from google.genai.types import GenerateContentConfig

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from event_bus import get_event_bus, parse_pubsub_message

app = Flask(__name__)
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phantom.layer5")

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "phantom-hack2skill")
REGION = os.environ.get("GCP_REGION", "us-central1")
REPORTS_BUCKET = os.environ.get("REPORTS_BUCKET", f"{PROJECT_ID}-phantom-reports")
ABUSEIPDB_KEY = os.environ.get("ABUSEIPDB_API_KEY", "")

ai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)
storage_client = storage.Client(project=PROJECT_ID)

# ---------------------------------------------------------------------------
# Color Palette
# ---------------------------------------------------------------------------
BG_DARK = HexColor("#0D1117")
BG_CARD = HexColor("#161B22")
BG_TABLE_HEADER = HexColor("#1A2332")
BG_TABLE_ROW = HexColor("#0D1117")
BG_TABLE_ALT = HexColor("#131920")
ACCENT_GREEN = HexColor("#00FF88")
ACCENT_RED = HexColor("#FF4444")
ACCENT_YELLOW = HexColor("#FFAA00")
ACCENT_BLUE = HexColor("#58A6FF")
TEXT_PRIMARY = HexColor("#E6EDF3")
TEXT_SECONDARY = HexColor("#8B949E")
TEXT_DIM = HexColor("#484F58")

# ---------------------------------------------------------------------------
# PDF Styles
# ---------------------------------------------------------------------------
STYLES = {
    "title": ParagraphStyle(
        "title", fontSize=24, textColor=ACCENT_GREEN,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6,
    ),
    "subtitle": ParagraphStyle(
        "subtitle", fontSize=14, textColor=TEXT_SECONDARY,
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=20,
    ),
    "h1": ParagraphStyle(
        "h1", fontSize=18, textColor=ACCENT_GREEN,
        fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=10,
    ),
    "h2": ParagraphStyle(
        "h2", fontSize=14, textColor=ACCENT_BLUE,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=8,
    ),
    "body": ParagraphStyle(
        "body", fontSize=10, textColor=TEXT_PRIMARY,
        fontName="Helvetica", leading=14, spaceAfter=6,
    ),
    "body_dim": ParagraphStyle(
        "body_dim", fontSize=9, textColor=TEXT_SECONDARY,
        fontName="Helvetica", leading=12, spaceAfter=4,
    ),
    "code": ParagraphStyle(
        "code", fontSize=8, textColor=ACCENT_GREEN,
        fontName="Courier", leading=11, spaceAfter=2,
    ),
    "metric_value": ParagraphStyle(
        "metric_value", fontSize=24, textColor=ACCENT_GREEN,
        fontName="Helvetica-Bold", alignment=TA_CENTER,
    ),
    "metric_label": ParagraphStyle(
        "metric_label", fontSize=9, textColor=TEXT_SECONDARY,
        fontName="Helvetica", alignment=TA_CENTER,
    ),
    "warning": ParagraphStyle(
        "warning", fontSize=10, textColor=ACCENT_RED,
        fontName="Helvetica-Bold", spaceAfter=6,
    ),
}

TABLE_STYLE_DARK = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), BG_TABLE_HEADER),
    ("TEXTCOLOR", (0, 0), (-1, 0), ACCENT_GREEN),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 1), (-1, -1), 8),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_TABLE_ROW, BG_TABLE_ALT]),
    ("GRID", (0, 0), (-1, -1), 0.5, TEXT_DIM),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
])


def draw_page_background(canvas_obj, doc):
    """Draw dark background on every page."""
    canvas_obj.saveState()
    canvas_obj.setFillColor(BG_DARK)
    canvas_obj.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    # Footer
    canvas_obj.setFillColor(TEXT_DIM)
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.drawString(30, 20, f"PHANTOM Threat Intelligence Report | Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    canvas_obj.drawRightString(A4[0] - 30, 20, f"Page {doc.page}")
    # Top accent line
    canvas_obj.setStrokeColor(ACCENT_GREEN)
    canvas_obj.setLineWidth(2)
    canvas_obj.line(0, A4[1] - 3, A4[0], A4[1] - 3)
    canvas_obj.restoreState()


# ---------------------------------------------------------------------------
# External API Calls
# ---------------------------------------------------------------------------
def get_geo_data(ip: str) -> dict:
    """Get geolocation data from ip-api.com."""
    try:
        resp = http_requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "lat": data.get("lat", 0),
                    "lon": data.get("lon", 0),
                    "isp": data.get("isp", "Unknown"),
                    "org": data.get("org", "Unknown"),
                    "as": data.get("as", ""),
                }
    except Exception as e:
        logger.warning(f"Geo lookup failed for {ip}: {e}")
    return {"country": "Unknown", "city": "Unknown", "lat": 0, "lon": 0, "isp": "Unknown"}


def get_abuse_data(ip: str) -> dict:
    """Get IP reputation from AbuseIPDB."""
    if not ABUSEIPDB_KEY:
        return {"abuse_score": "N/A", "total_reports": "N/A", "note": "API key not configured"}
    try:
        resp = http_requests.get(
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": ip, "maxAgeInDays": 90},
            headers={"Key": ABUSEIPDB_KEY, "Accept": "application/json"},
            timeout=5,
        )
        if resp.status_code == 200:
            d = resp.json().get("data", {})
            return {
                "abuse_score": d.get("abuseConfidenceScore", 0),
                "total_reports": d.get("totalReports", 0),
                "usage_type": d.get("usageType", "Unknown"),
                "domain": d.get("domain", "Unknown"),
            }
    except Exception as e:
        logger.warning(f"AbuseIPDB lookup failed for {ip}: {e}")
    return {"abuse_score": "N/A", "total_reports": "N/A"}


# ---------------------------------------------------------------------------
# Gemini Report Generation
# ---------------------------------------------------------------------------
def generate_executive_summary(session: dict, commands: list) -> str:
    """Use Gemini to write an executive summary."""
    prompt = f"""Write a concise executive summary (3-4 paragraphs) for a cybersecurity 
threat intelligence report. Use professional, technical language.

Session details:
- Attacker IP: {session.get('attacker_ip', 'Unknown')}
- Session type: {session.get('session_type', 'REAL')}
- Threat score: {session.get('threat_score', 0)}/100
- Skill level: {session.get('skill_level', 'Unknown')}
- Intent: {session.get('intent', 'Unknown')}
- Total commands: {session.get('command_count', 0)}
- MITRE tactics: {', '.join(session.get('mitre_tactics', []))}

Sample commands (first 10):
{chr(10).join(c.get('raw_command', '') for c in commands[:10])}

Write the summary focusing on: threat assessment, attacker methodology, 
potential impact, and urgency level."""

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
            config=GenerateContentConfig(temperature=0.4, max_output_tokens=1024),
        )
        return response.text
    except Exception as e:
        logger.warning(f"Gemini exec summary failed: {e}")
        return (f"An attacker from IP {session.get('attacker_ip', 'Unknown')} "
                f"was detected with threat score {session.get('threat_score', 0)}/100. "
                f"Skill level: {session.get('skill_level', 'Unknown')}. "
                f"Primary intent: {session.get('intent', 'Unknown')}.")


def generate_mitre_mapping(commands: list) -> list:
    """Use Gemini to map commands to MITRE ATT&CK framework."""
    cmd_texts = [c.get("raw_command", "") for c in commands[:20]]
    prompt = f"""Map these attacker commands to MITRE ATT&CK tactics and techniques.
Return a JSON array of objects with fields: tactic_id, tactic_name, technique_id, 
technique_name, evidence (the command that triggered it).
Maximum 10 mappings.

Commands:
{chr(10).join(cmd_texts)}"""

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
            config=GenerateContentConfig(
                temperature=0.2, max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        mappings = json.loads(text.strip())
        if isinstance(mappings, list):
            return mappings[:10]
        if isinstance(mappings, dict):
            return [mappings]
        return []
    except Exception as e:
        logger.warning(f"Gemini MITRE mapping failed: {e}")
        return [
            {"tactic_id": "TA0007", "tactic_name": "Discovery",
             "technique_id": "T1083", "technique_name": "File and Directory Discovery",
             "evidence": "ls, find commands"},
        ]


def generate_recommendations(session: dict) -> str:
    """Use Gemini to generate security recommendations."""
    prompt = f"""Based on this honeypot session analysis, provide 5-7 specific, 
actionable security recommendations. Be concise and technical.

Threat score: {session.get('threat_score', 0)}/100
Skill level: {session.get('skill_level', 'Unknown')}
Intent: {session.get('intent', 'Unknown')}
MITRE tactics observed: {', '.join(session.get('mitre_tactics', []))}

Format as numbered list."""

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
            config=GenerateContentConfig(temperature=0.4, max_output_tokens=1024),
        )
        return response.text
    except Exception as e:
        logger.warning(f"Gemini recommendations failed: {e}")
        return ("1. Implement network segmentation\n"
                "2. Enable multi-factor authentication\n"
                "3. Deploy intrusion detection systems\n"
                "4. Review and rotate all credentials\n"
                "5. Update firewall rules")


# ---------------------------------------------------------------------------
# PDF Builder
# ---------------------------------------------------------------------------
def build_report_pdf(session: dict, commands: list,
                     exec_summary: str, mitre_mappings: list,
                     recommendations: str, geo: dict, abuse: dict) -> BytesIO:
    """Build the complete PDF report and return as BytesIO."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=30, rightMargin=30,
        topMargin=40, bottomMargin=40,
    )
    story = []
    S = STYLES

    # â”€â”€ COVER PAGE â”€â”€
    story.append(Spacer(1, 80))
    story.append(Spacer(1, 20))
    story.append(Paragraph("PHANTOM", S["title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("AI HONEYPOT DECEPTION SYSTEM", S["subtitle"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="80%", color=ACCENT_GREEN, thickness=1))
    story.append(Spacer(1, 20))
    story.append(Paragraph("THREAT INTELLIGENCE REPORT", ParagraphStyle(
        "cover_h", fontSize=20, textColor=TEXT_PRIMARY,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=30,
    )))

    # Metrics row
    sid = session.get("session_id", "N/A")
    score = session.get("threat_score", 0)
    skill = session.get("skill_level", "Unknown")
    intent = session.get("intent", "Unknown")
    score_color = ACCENT_GREEN if score < 40 else (ACCENT_YELLOW if score < 70 else ACCENT_RED)

    metrics_data = [
        ["THREAT SCORE", "SKILL LEVEL", "INTENT", "COMMANDS"],
        [str(score), skill.upper(), intent.upper().replace("_", " "),
         str(session.get("command_count", 0))],
    ]
    metrics_table = Table(metrics_data, colWidths=[130, 130, 130, 130])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_SECONDARY),
        ("TEXTCOLOR", (0, 1), (-1, 1), ACCENT_GREEN),
        ("TEXTCOLOR", (0, 1), (0, 1), score_color),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, TEXT_DIM),
    ]))
    story.append(metrics_table)

    story.append(Spacer(1, 20))
    session_type = session.get("session_type", "REAL")
    type_color = ACCENT_YELLOW if session_type == "SIMULATED" else ACCENT_RED
    story.append(Paragraph(
        f'<font color="{type_color}">[{session_type} SESSION]</font> &nbsp; | &nbsp; '
        f'Session ID: {sid} &nbsp; | &nbsp; '
        f'IP: {session.get("attacker_ip", "N/A")}',
        ParagraphStyle("cover_meta", fontSize=10, textColor=TEXT_SECONDARY,
                        fontName="Helvetica", alignment=TA_CENTER),
    ))

    story.append(PageBreak())

    # â”€â”€ 1. EXECUTIVE SUMMARY â”€â”€
    story.append(Paragraph("1. EXECUTIVE SUMMARY", S["h1"]))
    story.append(HRFlowable(width="100%", color=ACCENT_GREEN, thickness=0.5))
    for para in exec_summary.split("\n\n"):
        if para.strip():
            clean = para.strip().replace("\n", " ")
            story.append(Paragraph(clean, S["body"]))
    story.append(Spacer(1, 10))

    # â”€â”€ 2. ATTACKER PROFILE â”€â”€
    story.append(Paragraph("2. ATTACKER PROFILE", S["h1"]))
    story.append(HRFlowable(width="100%", color=ACCENT_GREEN, thickness=0.5))

    profile_data = [
        ["Property", "Value"],
        ["IP Address", session.get("attacker_ip", "N/A")],
        ["Country", geo.get("country", "N/A")],
        ["City", geo.get("city", "N/A")],
        ["ISP", geo.get("isp", "N/A")],
        ["Organization", geo.get("org", geo.get("isp", "N/A"))],
        ["Coordinates", f"{geo.get('lat', 0)}, {geo.get('lon', 0)}"],
        ["Abuse Score", str(abuse.get("abuse_score", "N/A"))],
        ["Total Reports", str(abuse.get("total_reports", "N/A"))],
        ["Skill Level", session.get("skill_level", "N/A").upper()],
        ["Primary Intent", session.get("intent", "N/A").replace("_", " ").title()],
    ]
    profile_table = Table(profile_data, colWidths=[160, 370])
    profile_table.setStyle(TABLE_STYLE_DARK)
    story.append(profile_table)

    # â”€â”€ 3. ATTACK TIMELINE â”€â”€
    story.append(Spacer(1, 10))
    story.append(Paragraph("3. ATTACK TIMELINE", S["h1"]))
    story.append(HRFlowable(width="100%", color=ACCENT_GREEN, thickness=0.5))

    timeline_header = ["#", "Command", "RL Action", "Confidence", "Reward"]
    timeline_rows = [timeline_header]
    for i, cmd in enumerate(commands[:30], 1):
        timeline_rows.append([
            str(i),
            cmd.get("raw_command", "")[:50],
            cmd.get("rl_action", "N/A"),
            f"{cmd.get('rl_confidence', 0):.0%}",
            f"+{cmd.get('rl_reward', 0)}",
        ])

    if timeline_rows:
        t = Table(timeline_rows, colWidths=[30, 230, 120, 70, 60])
        t.setStyle(TABLE_STYLE_DARK)
        story.append(t)

    if len(commands) > 30:
        story.append(Paragraph(
            f"... and {len(commands) - 30} more commands (truncated)", S["body_dim"]
        ))

    story.append(PageBreak())

    # â”€â”€ 4. MITRE ATT&CK MAPPING â”€â”€
    story.append(Paragraph("4. MITRE ATT&CK MAPPING", S["h1"]))
    story.append(HRFlowable(width="100%", color=ACCENT_GREEN, thickness=0.5))

    if mitre_mappings:
        mitre_header = ["Tactic", "Technique", "Evidence"]
        mitre_rows = [mitre_header]
        for m in mitre_mappings:
            tactic = f"{m.get('tactic_id', '')} {m.get('tactic_name', '')}"
            technique = f"{m.get('technique_id', '')} {m.get('technique_name', '')}"
            evidence = str(m.get("evidence", ""))[:60]
            mitre_rows.append([tactic, technique, evidence])

        mt = Table(mitre_rows, colWidths=[160, 200, 170])
        mt.setStyle(TABLE_STYLE_DARK)
        story.append(mt)
    else:
        story.append(Paragraph("No MITRE mappings generated.", S["body_dim"]))

    # â”€â”€ 5. BEHAVIORAL FINGERPRINT â”€â”€
    story.append(Spacer(1, 10))
    story.append(Paragraph("5. BEHAVIORAL FINGERPRINT", S["h1"]))
    story.append(HRFlowable(width="100%", color=ACCENT_GREEN, thickness=0.5))

    tools = session.get("tools_detected", [])
    story.append(Paragraph(f"<b>Skill Level:</b> {session.get('skill_level', 'N/A').upper()}", S["body"]))
    story.append(Paragraph(f"<b>Primary Intent:</b> {session.get('intent', 'N/A').replace('_', ' ').title()}", S["body"]))
    story.append(Paragraph(f"<b>Intent Confidence:</b> {session.get('intent_confidence', 0):.0%}", S["body"]))
    story.append(Paragraph(f"<b>Tools Detected:</b> {', '.join(tools) if tools else 'None identified'}", S["body"]))
    story.append(Paragraph(f"<b>MITRE Tactics:</b> {', '.join(session.get('mitre_tactics', []))}", S["body"]))

    # â”€â”€ 6. RL AGENT LOG â”€â”€
    story.append(Spacer(1, 10))
    story.append(Paragraph("6. RL AGENT DECISION LOG", S["h1"]))
    story.append(HRFlowable(width="100%", color=ACCENT_GREEN, thickness=0.5))
    story.append(Paragraph(f"<b>Cumulative Reward:</b> +{session.get('cumulative_reward', 0)}", S["body"]))
    story.append(Paragraph(f"<b>Total Decisions:</b> {session.get('command_count', 0)}", S["body"]))

    # Action distribution
    from collections import Counter
    actions = [c.get("rl_action", "UNKNOWN") for c in commands if c.get("rl_action")]
    if actions:
        action_counts = Counter(actions)
        dist_header = ["Action", "Count", "Percentage"]
        dist_rows = [dist_header]
        for action, count in action_counts.most_common():
            pct = f"{count/len(actions)*100:.1f}%"
            dist_rows.append([action, str(count), pct])
        dt = Table(dist_rows, colWidths=[200, 100, 100])
        dt.setStyle(TABLE_STYLE_DARK)
        story.append(dt)

    # â”€â”€ 7. RECOMMENDATIONS â”€â”€
    story.append(Spacer(1, 10))
    story.append(Paragraph("7. RECOMMENDATIONS", S["h1"]))
    story.append(HRFlowable(width="100%", color=ACCENT_GREEN, thickness=0.5))
    for line in recommendations.split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), S["body"]))

    # â”€â”€ FOOTER â”€â”€
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", color=TEXT_DIM, thickness=0.5))
    story.append(Paragraph(
        "Generated by PHANTOM AI Honeypot Deception System | "
        "This report is classified. Handle according to your organization's security policy.",
        S["body_dim"],
    ))

    doc.build(story, onFirstPage=draw_page_background, onLaterPages=draw_page_background)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Report Generation Pipeline
# ---------------------------------------------------------------------------
def generate_report(session_id: str) -> dict:
    """Full report generation pipeline."""
    eb = get_event_bus()
    session = eb.get_session(session_id)
    if not session:
        return {"error": f"Session {session_id} not found"}

    commands = eb.get_commands(session_id)
    ip = session.get("attacker_ip", "unknown")
    logger.info(f"Generating report for session {session_id} ({ip})")

    # Gather data
    geo = session.get("geo", {})
    if not geo or geo.get("country") == "Unknown":
        geo = get_geo_data(ip)
        eb.update_session(session_id, {"geo": geo})

    abuse = get_abuse_data(ip)
    exec_summary = generate_executive_summary(session, commands)
    mitre_mappings = generate_mitre_mapping(commands)
    recommendations = generate_recommendations(session)

    # Build PDF
    pdf_buffer = build_report_pdf(
        session, commands, exec_summary, mitre_mappings,
        recommendations, geo, abuse
    )

    # Upload to Cloud Storage
    try:
        bucket = storage_client.bucket(REPORTS_BUCKET)
        blob = bucket.blob(f"reports/{session_id}.pdf")
        blob.upload_from_file(pdf_buffer, content_type="application/pdf")
        pdf_url = f"https://storage.googleapis.com/{REPORTS_BUCKET}/reports/{session_id}.pdf"
        # make_public() disabled - bucket uses uniform access
    except Exception as e:
        logger.warning(f"Cloud Storage upload failed: {e}")
        pdf_url = f"/api/report/{session_id}/download"

    # Save metadata
    eb.save_report_metadata(
        session_id, pdf_url, exec_summary, mitre_mappings
    )

    logger.info(f"Report generated: {pdf_url}")
    return {
        "session_id": session_id,
        "pdf_url": pdf_url,
        "executive_summary": exec_summary[:200],
        "mitre_count": len(mitre_mappings),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/generate-report", methods=["POST"])
def generate_report_endpoint():
    """Manual trigger for report generation."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    result = generate_report(session_id)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/report/<session_id>/download")
def download_report(session_id):
    """Download a generated report PDF."""
    eb = get_event_bus()
    report = eb.db.collection("reports").document(session_id).get()
    if not report.exists:
        # Generate on the fly
        result = generate_report(session_id)
        if "error" in result:
            return jsonify(result), 404

    # Try to get from Cloud Storage
    try:
        bucket = storage_client.bucket(REPORTS_BUCKET)
        blob = bucket.blob(f"reports/{session_id}.pdf")
        pdf_bytes = BytesIO(blob.download_as_bytes())
        return send_file(
            pdf_bytes, mimetype="application/pdf",
            as_attachment=True,
            download_name=f"PHANTOM_Report_{session_id}.pdf"
        )
    except Exception as e:
        logger.error(f"Failed to download report: {e}")
        return jsonify({"error": "Report not found in storage"}), 404


@app.route("/api/pubsub/disconnect", methods=["POST"])
def pubsub_disconnect():
    """Pub/Sub push handler for attacker disconnect events."""
    data = parse_pubsub_message(request)
    if not data:
        return jsonify({"error": "Invalid message"}), 400

    session_id = data.get("session_id", "")
    if not session_id:
        return jsonify({"status": "skipped"}), 200

    logger.info(f"Disconnect trigger â€” generating report for {session_id}")
    result = generate_report(session_id)
    return jsonify(result), 200


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "phantom-layer5-reports"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)









