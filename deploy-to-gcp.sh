#!/bin/bash

# AI Tutor - Google Cloud Deployment Script
# This script deploys the AI Tutor application to Google Cloud Platform

set -e

echo "🚀 Starting AI Tutor deployment to Google Cloud Platform..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Error: Not authenticated with gcloud. Please run:"
    echo "   gcloud auth login"
    exit 1
fi

# Get current project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No project ID set. Please run:"
    echo "   gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Project ID: $PROJECT_ID"

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Set the region
REGION="asia-southeast1"
gcloud config set run/region $REGION

echo "🌍 Region: $REGION"

# Build and deploy using Cloud Build
echo "🏗️  Building and deploying with Cloud Build..."
cd backend

# Submit build
gcloud builds submit --config cloudbuild.yaml .

# Get the service URL
SERVICE_URL=$(gcloud run services describe ai-tutor --region=$REGION --format="value(status.url)")

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo "📚 LTI Config URL: $SERVICE_URL/lti/config"
echo "🤖 Widget URL: $SERVICE_URL/widget"
echo ""
echo "🔧 Next steps:"
echo "1. Update your Canvas LTI app configuration with the new domain:"
echo "   $SERVICE_URL"
echo "2. Test the LTI integration with the new URLs"
echo "3. Monitor the service in Google Cloud Console"
echo ""
echo "📊 Monitor your service:"
echo "   https://console.cloud.google.com/run/detail/$REGION/ai-tutor" 