# PHANTOM — AI Honeypot Deception System

PHANTOM is a 5-layer cloud-native honeypot system that uses Vertex AI Gemini to generate realistic fake corporate environments to lure attackers, uses Reinforcement Learning to dynamically deceive them, analyzes their behavior, and generates professional threat intelligence PDF reports.

## Architecture

*   **Layer 1: Honeypot & Trap (Cloud Run)** - Flask app exposing vulnerable endpoints. Includes an anomaly detector (Isolation Forest) and a simulation endpoint.
*   **Layer 2: Company Bible Generator (Cloud Run)** - Uses Vertex AI Gemini to generate a complete, coherent fake corporate identity (staff, databases, AWS keys, git logs).
*   **Layer 3: RL Decision Agent (Cloud Run)** - High-speed (<100ms) rule-based decision engine that determines what fake data to serve the attacker to keep them engaged.
*   **Layer 4: Behavioral Analysis (Cloud Run)** - Uses Gemini to classify attacker intent (data theft, sabotage, etc.) and heuristic rules to assess skill level (Script Kiddie vs APT).
*   **Layer 5: Report Generator (Cloud Run)** - Uses ReportLab to generate dark-themed, professional PDF threat intel reports, using Gemini to write the executive summary and map actions to the MITRE ATT&CK framework.
*   **Frontend (React/Firebase)** - A real-time dashboard visualizing the attack in progress.

## Prerequisites

1.  Google Cloud project with billing enabled.
2.  `gcloud` CLI installed and authenticated.
3.  Terraform installed.
4.  Node.js installed (for frontend).

## One-Command Setup

See `SETUP.md` for full deployment instructions.
