#!/usr/bin/env bash
# Deploy one of the ADK agents to Google Cloud Run.
#
# Usage (from the "12. ADK" folder, with the venv activated):
#     ./deploy.sh                          deploys agent_6_model_callback
#     ./deploy.sh agent_3_sequential       deploys any other agent folder
#
# One-time setup:
#     brew install --cask google-cloud-sdk         # installs gcloud
#     gcloud auth login
#     gcloud config set project learn-ai-511809
#     gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
#         artifactregistry.googleapis.com aiplatform.googleapis.com
#
# How it works: `adk deploy cloud_run` builds a container with ADK and the agent
# folder, and deploys it with `gcloud run deploy`. Only the agent folder is
# copied, so the .env file at the repo root (with your keys) is NOT uploaded.
# In the cloud the agent calls Gemini through Vertex AI using the Cloud Run
# service account - no GOOGLE_API_KEY needed, usage is billed to the project.
set -euo pipefail

PROJECT_ID="learn-ai-511809"
# Used both for Cloud Run and for the Vertex AI Gemini calls
# (ADK sets GOOGLE_CLOUD_LOCATION to this region inside the container).
# If a model is ever "not found" here, add --set-env-vars=GOOGLE_CLOUD_LOCATION=global
REGION="europe-west2"
AGENT="${1:-agent_6_model_callback}"

# `adk deploy` uses gcloud for the actual upload, so check for it first
if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is not installed. Run: brew install --cask google-cloud-sdk" >&2
  echo "then open a new terminal and do the one-time setup at the top of this script." >&2
  exit 1
fi

# Cloud Run service names may only use lowercase letters, digits and hyphens
SERVICE_NAME="${AGENT//_/-}"

# Extra flags passed through to `gcloud run deploy` (after the "--")
GCLOUD_ARGS=()

case "$AGENT" in
  agent_1_ollama)
    echo "agent_1_ollama needs a local Ollama server, so it can't run on Cloud Run." >&2
    exit 1
    ;;
  agent_2_gemini_tools)
    # The weather tools need the OpenWeatherMap key. It is read from the local
    # .env and set as a Cloud Run environment variable (for real apps, store
    # it in Secret Manager and use --set-secrets instead).
    OPENWEATHER_API_KEY="$(grep '^OPENWEATHER_API_KEY=' ../.env | cut -d= -f2-)"
    GCLOUD_ARGS+=(--set-env-vars="OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}")
    ;;
esac

# --with_ui deploys the `adk web` chat UI, without it only the REST API is deployed.
# gcloud asks whether to allow unauthenticated access: "y" makes the URL public.
adk deploy cloud_run \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --service_name="$SERVICE_NAME" \
  --app_name="$AGENT" \
  --with_ui \
  "$AGENT" \
  ${GCLOUD_ARGS[@]+-- "${GCLOUD_ARGS[@]}"}
