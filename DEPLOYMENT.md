# Deployment Guide

This guide covers deploying the HPV Vaccine Chatbot using Docker and Google Cloud Run.

## Prerequisites

- Docker installed locally
- Google Cloud SDK (`gcloud`) installed and configured
- A Google Cloud project with billing enabled
- API keys for:
  - OpenAI (for embeddings and chat completions)
  - Pinecone (for vector database)

## Environment Variables

The application requires the following environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `PINECONE_API_KEY` | ✅ | Pinecone API key |
| `PINECONE_INDEX_NAME` | ✅ | Name of your Pinecone index |
| `SECRET_KEY` | ⚠️ | Flask session secret (recommended for production) |
| `PORT` | ❌ | Server port (defaults to 8000/8080) |
| `SYNTHESIS_STRATEGY` | ❌ | Context synthesis strategy |
| `RAG_K` | ❌ | Number of chunks from similarity search |
| `MAX_NEW_TOKENS` | ❌ | Maximum tokens to generate |

## Local Development

### Option 1: Using .env file (Recommended)

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your API keys:
   ```bash
   OPENAI_API_KEY=sk-your-openai-key
   PINECONE_API_KEY=your-pinecone-key
   PINECONE_INDEX_NAME=hpv-guide-v2
   SECRET_KEY=your-secret-key
   ```

3. Run with Poetry:
   ```bash
   poetry install
   poetry run python chatbot/web_app.py
   ```

### Option 2: Using Docker Compose

1. Create your `.env` file as shown above

2. Build and run:
   ```bash
   docker-compose up --build
   ```

3. Access the app at http://localhost (via Nginx reverse proxy)

## Google Cloud Run Deployment

### Method 1: Using Environment Variables (Simple)

1. Set up your environment variables:
   ```bash
   export OPENAI_API_KEY="sk-your-openai-key"
   export PINECONE_API_KEY="your-pinecone-key"
   export PINECONE_INDEX_NAME="hpv-guide-v2"
   export SECRET_KEY="your-flask-secret"
   ```

2. Deploy:
   ```bash
   ./deploy.sh your-project-id
   ```

### Method 2: Using .env file

1. Create your `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. Deploy (the script will read from `.env`):
   ```bash
   ./deploy.sh your-project-id
   ```

### Method 3: Using Google Cloud Secret Manager (Recommended for Production)

Secret Manager provides secure, auditable storage for sensitive configuration.

1. Enable the Secret Manager API:
   ```bash
   gcloud services enable secretmanager.googleapis.com
   ```

2. Create your secrets:
   ```bash
   echo -n "sk-your-openai-key" | gcloud secrets create openai-api-key --data-file=-
   echo -n "your-pinecone-key" | gcloud secrets create pinecone-api-key --data-file=-
   echo -n "hpv-guide-v2" | gcloud secrets create pinecone-index-name --data-file=-
   echo -n "your-flask-secret" | gcloud secrets create flask-secret-key --data-file=-
   ```

3. Deploy with the `--use-secrets` flag:
   ```bash
   ./deploy.sh your-project-id --use-secrets
   ```

## Updating Secrets

### Update via gcloud:
```bash
echo -n "new-api-key" | gcloud secrets versions add openai-api-key --data-file=-
```

Then redeploy the service:
```bash
gcloud run services update hpv-vaccine-chatbot --region us-central1
```

## Troubleshooting

### "Vector store is unavailable" Error

This error occurs when the Pinecone client fails to initialize. Common causes:

1. **Missing environment variables**: Ensure `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` are set.
   
   Check with:
   ```bash
   # In Cloud Run logs
   gcloud run logs read --service=hpv-vaccine-chatbot --region=us-central1
   ```

2. **Invalid API key**: Verify your Pinecone API key is correct and active.

3. **Index doesn't exist**: Make sure the Pinecone index specified in `PINECONE_INDEX_NAME` exists in your Pinecone dashboard.

### Environment Variables Not Working

If environment variables from `.env` aren't being picked up:

1. **Local development**: Make sure you're in the project root directory when running the app.

2. **Docker**: The `.env` file must be in the same directory as `docker-compose.yml`.

3. **Cloud Run**: Environment variables are set at deploy time. To update, redeploy or use:
   ```bash
   gcloud run services update hpv-vaccine-chatbot \
     --region us-central1 \
     --set-env-vars "PINECONE_INDEX_NAME=new-index-name"
   ```

### Viewing Cloud Run Logs

```bash
# Stream logs
gcloud run logs read --service=hpv-vaccine-chatbot --region=us-central1 --tail=50

# Follow logs in real-time
gcloud alpha run logs tail hpv-vaccine-chatbot --region=us-central1
```

## Security Best Practices

1. **Never commit `.env` files** - They're already in `.gitignore`
2. **Use Secret Manager in production** - More secure than environment variables
3. **Rotate API keys regularly** - Update secrets when keys are rotated
4. **Set a strong `SECRET_KEY`** - Generate with:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. **Restrict service access** - Consider using Cloud Run IAM instead of `--allow-unauthenticated`
