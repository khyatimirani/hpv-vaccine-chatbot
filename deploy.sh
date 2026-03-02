#!/bin/bash

# HPV Vaccine Chatbot Deployment Script
# Usage: ./deploy.sh [project-id]

set -e

PROJECT_ID=${1:-"your-project-id"}
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
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --set-env-vars PINECONE_API_KEY=$PINECONE_API_KEY \
  --set-env-vars PINECONE_INDEX_NAME=$PINECONE_INDEX_NAME

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
