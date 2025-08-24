#!/bin/bash

# Script to setup Secret Manager for MLB Stats Assistant
# Usage: ./scripts/setup-secret.sh [password]

set -e

# Get project ID
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP project is set. Please run 'gcloud config set project YOUR_PROJECT_ID'"
    exit 1
fi

# Get password from command line or prompt
if [ $# -eq 1 ]; then
    PASSWORD="$1"
else
    echo "Enter the password for MLB Stats Assistant:"
    read -s PASSWORD
fi

if [ -z "$PASSWORD" ]; then
    echo "Error: Password cannot be empty"
    exit 1
fi

echo "Setting up Secret Manager for project: $PROJECT_ID"

# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# Create the secret
echo "Creating secret 'VITE_APP_PASSWORD'..."
echo "$PASSWORD" | gcloud secrets create VITE_APP_PASSWORD --data-file=- || {
    echo "Secret might already exist. Updating with new version..."
    echo "$PASSWORD" | gcloud secrets versions add VITE_APP_PASSWORD --data-file=-
}

# Get Cloud Build service account
CLOUD_BUILD_SA="$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"

# Grant Cloud Build access to the secret
echo "Granting Cloud Build access to the secret..."
gcloud secrets add-iam-policy-binding VITE_APP_PASSWORD \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/secretmanager.secretAccessor"

echo "✅ Secret Manager setup complete!"
echo ""
echo "You can now deploy using:"
echo "  gcloud builds submit --config cloudbuild.yaml ."
echo ""
echo "To update the password later, run:"
echo "  echo 'new_password' | gcloud secrets versions add VITE_APP_PASSWORD --data-file=-"