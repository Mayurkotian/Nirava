# Deployment Strategy for Nirava

## Current Status

**Nirava is not deployed to a live public endpoint for this capstone submission.** 

The application runs locally via `python adk_main.py` to demonstrate full functionality for judging purposes. This document outlines the deployment architecture designed for production.

---

## Proposed Production Architecture

### Cloud Platform: Google Cloud Platform (GCP)

```
┌─────────────────────────────────────────────────────────────┐
│                     USER DEVICES                            │
│              (Mobile App / Web Browser)                     │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              GOOGLE CLOUD LOAD BALANCER                     │
│                  (Global HTTPS LB)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  CLOUD RUN SERVICE                          │
│            (Containerized Python App)                       │
│  • Auto-scaling: 0-100 instances                            │
│  • Region: us-central1                                      │
│  • Memory: 2GB per instance                                 │
│  • CPU: 2 vCPU                                              │
│  • Concurrency: 80 requests/instance                        │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Gemini   │  │ Cloud    │  │ Secret   │
│ API      │  │ Firestore│  │ Manager  │
│ (LLM)    │  │ (Sessions│  │ (API Keys│
└──────────┘  └──────────┘  └──────────┘
```

---

## Deployment Steps (Not Executed)

### 1. Containerization

**Dockerfile** (to be created):
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "adk_main.py"]
```

### 2. Cloud Run Deployment

```bash
# Authenticate with GCP
gcloud auth login

# Set project
gcloud config set project nirava-health-ai

# Build and deploy to Cloud Run
gcloud run deploy nirava \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 100 \
  --set-env-vars GOOGLE_API_KEY=secret-ref:gemini-api-key
```

### 3. Environment Configuration

**Environment Variables** (stored in Secret Manager):
- `GOOGLE_API_KEY`: Gemini API key
- `SESSION_STORAGE`: `firestore` (instead of in-memory)
- `LOG_LEVEL`: `INFO`

### 4. Session Persistence

**Migration from In-Memory to Firestore**:

Current:
```python
# services/session_service.py
class InMemorySessionService:
    def __init__(self):
        self.sessions = {}  # ❌ Lost on restart
```

Production:
```python
# services/session_service.py
from google.cloud import firestore

class FirestoreSessionService:
    def __init__(self):
        self.db = firestore.Client()
        self.collection = self.db.collection('sessions')
    
    def save_session(self, session):
        self.collection.document(session.session_id).set(session.to_dict())
    
    def get_session(self, session_id):
        doc = self.collection.document(session_id).get()
        return ConversationState.from_dict(doc.to_dict())
```

---

## Alternative: Vertex AI Agent Builder

For a fully managed agent deployment, Nirava could be deployed using **Vertex AI Agent Builder**:

### Benefits:
- **No infrastructure management**: Google handles scaling, monitoring, and updates
- **Built-in agent orchestration**: Native support for multi-agent systems
- **Integrated grounding**: Direct access to Google Search and enterprise data
- **Conversation history**: Automatic session management

### Deployment Steps:
1. Export agents to Vertex AI Agent Builder format
2. Configure agent skills and tools
3. Deploy to Dialogflow CX or Agent Builder
4. Expose via REST API or integrate with Google Assistant

---

## Cost Estimation (Production Scale)

### Assumptions:
- 10,000 users/month
- Average 5 messages per session
- 50,000 LLM calls/month

| Service | Cost |
|---------|------|
| **Cloud Run** (2GB, 2 vCPU) | ~$50/month |
| **Gemini API** (50K calls @ $0.00025/call) | ~$12.50/month |
| **Cloud Firestore** (10K sessions) | ~$5/month |
| **Cloud Load Balancer** | ~$18/month |
| **Total** | **~$85/month** |

---

## Monitoring & Observability

### Cloud Logging Integration
```python
# Already implemented in observability.py
import google.cloud.logging

client = google.cloud.logging.Client()
client.setup_logging()

logger.info("Agent execution started")  # ✅ Automatically sent to Cloud Logging
```

### Metrics Dashboard (Cloud Monitoring)
- **Agent Latency**: P50, P95, P99 response times
- **Success Rate**: % of successful agent executions
- **Error Rate**: % of fallback invocations
- **User Engagement**: Sessions per day, messages per session

---

## Security Considerations

### API Key Management
- ✅ **Never commit API keys** to GitHub
- ✅ Use **Secret Manager** for production
- ✅ Rotate keys every 90 days

### Data Privacy
- ✅ **No PII storage**: Sessions are ephemeral
- ✅ **HTTPS only**: All traffic encrypted
- ✅ **GDPR compliance**: Users can request data deletion

---

## Why Not Deployed for This Submission?

1. **Judging Requirements**: Competition does not require live deployment
2. **Cost Optimization**: Running locally avoids unnecessary GCP charges during evaluation
3. **Reproducibility**: Judges can run `python adk_main.py` without cloud setup
4. **Focus on Code Quality**: Prioritized robust architecture over deployment infrastructure

---

## Future Deployment Roadmap

**Phase 1 (Post-Capstone)**: Deploy to Cloud Run with Firestore
**Phase 2**: Add web UI (React + TailwindCSS)
**Phase 3**: Mobile app (React Native)
**Phase 4**: Migrate to Vertex AI Agent Builder for enterprise scale

---

## Reproduction Instructions for Judges

To run Nirava locally (no deployment needed):

```bash
# 1. Clone repository
git clone https://github.com/Mayurkotian/Nirava.git
cd Nirava

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API key
export GOOGLE_API_KEY="your-gemini-api-key"

# 4. Run application
python adk_main.py
```

**That's it!** The application runs fully locally with all features functional.

---

## Contact

For deployment questions or collaboration:
- **Email**: mayurkotian@gmail.com
- **GitHub**: https://github.com/Mayurkotian/Nirava
