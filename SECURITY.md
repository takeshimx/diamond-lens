# Security Configuration

## Frontend Password Authentication

The MLB Stats Assistant uses password authentication to protect access to the application.

### Local Development

1. Copy the example environment file:
   ```bash
   cp frontend/.env.example frontend/.env
   ```

2. Edit `frontend/.env` and set your password:
   ```
   VITE_APP_PASSWORD=your_secure_password_here
   ```

### Production Deployment (Cloud Run)

For production deployment, the password is stored securely in GCP Secret Manager.

#### Setup Secret Manager (One-time setup)

**Option 1: Use the setup script (recommended)**
```bash
./scripts/setup-secret.sh your_secure_production_password
```

**Option 2: Manual setup**
1. Create the secret in Secret Manager:
   ```bash
   # Create the secret
   echo "your_secure_production_password" | gcloud secrets create mlb-app-password --data-file=-
   
   # Grant Cloud Build access to the secret
   gcloud secrets add-iam-policy-binding mlb-app-password \
     --member="serviceAccount:$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@cloudbuild.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

2. Deploy the application:
   ```bash
   gcloud builds submit --config cloudbuild.yaml .
   ```

#### Update the password (when needed)

```bash
echo "new_secure_password" | gcloud secrets versions add mlb-app-password --data-file=-
```

### Security Notes

- The `.env` file is already in `.gitignore` and will not be committed to Git
- Production passwords are stored securely in GCP Secret Manager (not in source code)
- The password is passed as a build-time argument and embedded in the frontend build
- Cloud Build service account has minimal permissions (only secret accessor)
- For enhanced security, consider implementing proper authentication with JWT tokens or OAuth
- Use a strong, unique password for production deployments

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_APP_PASSWORD` | Password for accessing the application | `defaultpassword` |

## Important Security Considerations

⚠️ **Warning**: This is a simple client-side password implementation. The password will be visible in the compiled JavaScript code. For production use with sensitive data, implement proper server-side authentication.

For better security, consider:
- Server-side authentication with session management
- JWT token-based authentication
- OAuth integration
- Rate limiting for failed login attempts