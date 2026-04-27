# PHANTOM Setup Guide

## Prerequisites

1.  **Google Cloud SDK**: Install `gcloud` and log in:
    ```bash
    gcloud auth login
    gcloud auth application-default login
    gcloud config set project phantom-hack2skill
    ```
2.  **Terraform**: Install Terraform >= 1.5.0
3.  **Node.js**: Install Node.js >= 18 (for the React frontend)
4.  **Firebase CLI**: Install Firebase tools:
    ```bash
    npm install -g firebase-tools
    firebase login
    ```

## 1. Deploy Infrastructure

```bash
cd infrastructure
terraform init
terraform apply
```

This will output the URLs for all 5 Cloud Run services and the Cloud Storage bucket name.

## 2. Configure Environment Variables

Copy `.env.example` to `.env` in the root directory and fill in the values:

*   `GCP_PROJECT_ID`: phantom-hack2skill
*   `GCP_REGION`: us-central1
*   `REPORTS_BUCKET`: (From Terraform output)
*   `LAYER1_URL`: (From Terraform output)
*   `ABUSEIPDB_API_KEY`: Get a free key from abuseipdb.com (optional)

Update the `.env` equivalent for the frontend:
Create `frontend/.env` with the Firebase configuration:
```env
VITE_FIREBASE_API_KEY=your_key
VITE_FIREBASE_AUTH_DOMAIN=phantom-hack2skill.firebaseapp.com
VITE_FIREBASE_DATABASE_URL=https://phantom-hack2skill-default-rtdb.firebaseio.com
VITE_FIREBASE_PROJECT_ID=phantom-hack2skill
VITE_FIREBASE_STORAGE_BUCKET=phantom-hack2skill.appspot.com
VITE_FIREBASE_APP_ID=your_app_id
VITE_LAYER1_URL=https://phantom-layer1-honeypot-...
VITE_LAYER5_URL=https://phantom-layer5-reports-...
```

## 3. Deploy Backend Services (Cloud Build)

If you have Cloud Build connected to your GitHub repo, just push your code.
Alternatively, deploy manually using Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml .
```

## 4. Deploy Frontend

```bash
cd frontend
npm install
npm run build
firebase deploy --only hosting
```

## 5. Test the Demo

1.  Navigate to your Firebase Hosting URL (e.g., `https://phantom-hack2skill.web.app`).
2.  In the **Attack Simulation** panel, select an attack type and difficulty.
3.  Click **Launch Attack Demo**.
4.  Watch the Live Attack Feed, Threat Score Meter, and RL Agent Panel update in real-time.
5.  When the simulation completes (or if you click "Generate Report Now"), wait ~5 seconds and click the download button to get the generated Threat Intelligence PDF.
