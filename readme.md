pytest were failing becase pytest.ini was present or pythonpath was not mentioned
testing code
```bash
pytest -q

```


```bash
export LIVEKIT_URL="https://your-livekit.example.com"
export LIVEKIT_API_KEY="your_key"
export LIVEKIT_API_SECRET="your_secret"

pip install -r requirements.txt
functions-framework --target connection_details --port 8080
```


api call
```cURL
curl -s "http://localhost:8080?provider=elevenlabs&voice_id=EXAVITQu4vr4xnSDxMaL"
```

### Deploy (Gen2) with Secrets and CORS
Enable services:
```
gcloud services enable cloudfunctions.googleapis.com run.googleapis.com secretmanager.googleapis.com
```

Create secrets :
```
printf "%s" "your_key" | gcloud secrets create LIVEKIT_API_KEY --data-file=-
printf "%s" "your_secret" | gcloud secrets create LIVEKIT_API_SECRET --data-file=-
```

create 
```
gcloud secrets list --project=openlabel-lab-firebase
```

## One-time GCP setup (run once)
### Enable APIs :
gcloud services enable iamcredentials.googleapis.com iam.googleapis.com \
  cloudfunctions.googleapis.com run.googleapis.com secretmanager.googleapis.com


If you want all gcloud commands to use a service account instead of your Gmail account:

gcloud config set auth/impersonate_service_account gh-actions-ci@openlabel-lab-firebase.iam.gserviceaccount.com


To check if you’re impersonating someone else:
```
gcloud config get-value auth/impersonate_service_account
```