#!/bin/bash

# HPV Vaccine Chatbot Deployment Script
# Usage:
#   ./deploy.sh <project-id>               # pass API keys via environment variables
#   ./deploy.sh <project-id> --use-secrets # read keys from Google Cloud Secret Manager

set -e

PROJECT_ID=${1:-"your-project-id"}
USE_SECRETS=false
if [[ "$*" == *"--use-secrets"* ]]; then
    USE_SECRETS=true
fi

REGION="us-central1"
SERVICE_NAME="hpv-vaccine-chatbot"

echo "🚀 Deploying HPV Vaccine Chatbot to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first."
    exit 1
fi

# Validate required env vars when not using Secret Manager
if [ "$USE_SECRETS" = false ]; then
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "❌ OPENAI_API_KEY is not set. Export it or use --use-secrets."
        exit 1
    fi
    if [ -z "$PINECONE_API_KEY" ]; then
        echo "❌ PINECONE_API_KEY is not set. Export it or use --use-secrets."
        exit 1
    fi
fi

# Set the project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID

# Build and push the image
echo "🔨 Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

echo "📤 Pushing to Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
if [ "$USE_SECRETS" = true ]; then
    # Use Google Cloud Secret Manager — secrets must be created first:
    #   gcloud secrets create OPENAI_API_KEY --data-file=<(echo -n "$OPENAI_API_KEY")
    #   gcloud secrets create PINECONE_API_KEY --data-file=<(echo -n "$PINECONE_API_KEY")
    # The Cloud Run service account needs the Secret Manager Secret Accessor role.
    echo "🔐 Using Google Cloud Secret Manager for sensitive credentials..."
    gcloud run deploy $SERVICE_NAME \
      --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
      --platform managed \
      --region $REGION \
      --allow-unauthenticated \
      --memory 1Gi \
      --cpu 1 \
      --timeout 300 \
      --min-instances 0 \
      --max-instances 10 \
      --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest,PINECONE_API_KEY=PINECONE_API_KEY:latest \
      ${PINECONE_INDEX_NAME:+--set-env-vars PINECONE_INDEX_NAME=$PINECONE_INDEX_NAME}
else
    # Pass keys directly — only include PINECONE_INDEX_NAME when it is non-empty
    # to avoid overriding the application default with an empty string.
    ENV_VARS="OPENAI_API_KEY=$OPENAI_API_KEY,PINECONE_API_KEY=$PINECONE_API_KEY"
    if [ -n "$PINECONE_INDEX_NAME" ]; then
        ENV_VARS="$ENV_VARS,PINECONE_INDEX_NAME=$PINECONE_INDEX_NAME"
    fi
    gcloud run deploy $SERVICE_NAME \
      --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
      --platform managed \
      --region $REGION \
      --allow-unauthenticated \
      --memory 1Gi \
      --cpu 1 \
      --timeout 300 \
      --min-instances 0 \
      --max-instances 10 \
      --set-env-vars "$ENV_VARS"
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format 'value(status.url)')

echo "✅ Deployment complete!"
echo "🔗 Service URL: $SERVICE_URL"
echo "🏥 Health check: $SERVICE_URL/health"

# Test the deployment
echo "🧪 Testing health endpoint..."
curl -s $SERVICE_URL/health | jq . || echo "Health check response received"

echo "🎉 HPV Vaccine Chatbot is now live!"
