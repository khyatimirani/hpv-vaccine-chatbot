#!/bin/bash

# HPV Vaccine Chatbot Deployment Script for Google Cloud Run
# ===========================================================
#
# This script deploys the HPV Vaccine Chatbot to Google Cloud Run.
#
# PREREQUISITES:
# 1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
# 2. Authenticate: gcloud auth login
# 3. Set up your environment variables (see options below)
#
# USAGE:
#   Option 1 - Using Google Cloud Secret Manager (RECOMMENDED for production):
#     ./deploy.sh <project-id> --use-secrets
#
#   Option 2 - Using .env file:
#     cp .env.example .env  # Then fill in your values
#     ./deploy.sh <project-id>
#
#   Option 3 - Using exported environment variables:
#     export OPENAI_API_KEY="your-key"
#     export PINECONE_API_KEY="your-key"
#     export PINECONE_INDEX_NAME="your-index"
#     export SECRET_KEY="your-flask-secret"  # optional
#     ./deploy.sh <project-id>
#
# SETTING UP SECRET MANAGER (for --use-secrets option):
#   1. Enable Secret Manager API:
#      gcloud services enable secretmanager.googleapis.com
#
#   2. Create secrets:
#      echo -n "your-openai-key" | gcloud secrets create openai-api-key --data-file=-
#      echo -n "your-pinecone-key" | gcloud secrets create pinecone-api-key --data-file=-
#      echo -n "your-index-name" | gcloud secrets create pinecone-index-name --data-file=-
#      echo -n "your-flask-secret" | gcloud secrets create flask-secret-key --data-file=-
#
#   3. Grant Cloud Run access to secrets (done automatically by this script)

set -e

# Parse arguments
PROJECT_ID=${1:-"your-project-id"}
USE_SECRETS=false

for arg in "$@"; do
    case $arg in
        --use-secrets)
            USE_SECRETS=true
            shift
            ;;
    esac
done

REGION="us-central1"
SERVICE_NAME="hpv-vaccine-chatbot"

echo "🚀 Deploying HPV Vaccine Chatbot to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Using Secrets: $USE_SECRETS"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install it first."
    exit 1
fi

# Set the project
echo "📋 Setting project..."
gcloud config set project "$PROJECT_ID"

# Load environment variables from .env if it exists (for local dev)
if [ -f .env ]; then
    echo "📄 Loading environment variables from .env file..."
    set -o allexport
    # SC1091 disabled because .env file may not exist during linting but is validated at runtime
    # shellcheck disable=SC1091
    source .env
    set +o allexport
fi

# Validate required environment variables if not using secrets
if [ "$USE_SECRETS" = false ]; then
    MISSING_VARS=()

    if [ -z "$OPENAI_API_KEY" ]; then
        MISSING_VARS+=("OPENAI_API_KEY")
    fi

    if [ -z "$PINECONE_API_KEY" ]; then
        MISSING_VARS+=("PINECONE_API_KEY")
    fi

    if [ -z "$PINECONE_INDEX_NAME" ]; then
        MISSING_VARS+=("PINECONE_INDEX_NAME")
    fi

    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        echo "❌ Missing required environment variables: ${MISSING_VARS[*]}"
        echo ""
        echo "Please set them using one of these methods:"
        echo "  1. Copy .env.example to .env and fill in your values"
        echo "  2. Export them in your shell: export OPENAI_API_KEY='your-key'"
        echo "  3. Use --use-secrets flag with Google Cloud Secret Manager"
        echo ""
        echo "See the script header for detailed instructions."
        exit 1
    fi
fi

# Build and push the image
echo "🔨 Building Docker image..."
docker build -t "gcr.io/$PROJECT_ID/$SERVICE_NAME:latest" .

echo "📤 Pushing to Container Registry..."
docker push "gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."

if [ "$USE_SECRETS" = true ]; then
    # Using Secret Manager
    echo "🔐 Using Google Cloud Secret Manager for secrets..."

    # Grant Cloud Run service account access to secrets
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

    echo "🔑 Granting secret access to service account: $SERVICE_ACCOUNT"
    for secret in openai-api-key pinecone-api-key pinecone-index-name flask-secret-key; do
        gcloud secrets add-iam-policy-binding "$secret" \
            --member="serviceAccount:$SERVICE_ACCOUNT" \
            --role="roles/secretmanager.secretAccessor" \
            --project="$PROJECT_ID" 2>/dev/null || true
    done

    gcloud run deploy "$SERVICE_NAME" \
        --image "gcr.io/$PROJECT_ID/$SERVICE_NAME:latest" \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --memory 1Gi \
        --cpu 1 \
        --timeout 300 \
        --min-instances 0 \
        --max-instances 10 \
        --set-secrets "OPENAI_API_KEY=openai-api-key:latest,PINECONE_API_KEY=pinecone-api-key:latest,PINECONE_INDEX_NAME=pinecone-index-name:latest,SECRET_KEY=flask-secret-key:latest"
else
    # Using environment variables directly
    ENV_VARS="OPENAI_API_KEY=$OPENAI_API_KEY,PINECONE_API_KEY=$PINECONE_API_KEY,PINECONE_INDEX_NAME=$PINECONE_INDEX_NAME"

    # Add SECRET_KEY if set
    if [ -n "$SECRET_KEY" ]; then
        ENV_VARS="$ENV_VARS,SECRET_KEY=$SECRET_KEY"
    fi

    gcloud run deploy "$SERVICE_NAME" \
        --image "gcr.io/$PROJECT_ID/$SERVICE_NAME:latest" \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --memory 1Gi \
        --cpu 1 \
        --timeout 300 \
        --min-instances 0 \
        --max-instances 10 \
        --set-env-vars "$ENV_VARS"
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "🔗 Service URL: $SERVICE_URL"
echo "🏥 Health check: $SERVICE_URL/health"

# Test the deployment
echo ""
echo "🧪 Testing health endpoint..."
curl -s "$SERVICE_URL/health" | jq . || echo "Health check response received"

echo ""
echo "🎉 HPV Vaccine Chatbot is now live!"
echo ""
echo "📝 Next steps:"
echo "   - Visit $SERVICE_URL to use the chatbot"
echo "   - Monitor logs: gcloud run logs read --service=$SERVICE_NAME --region=$REGION"
echo "   - Update secrets: gcloud secrets versions add <secret-name> --data-file=-"
