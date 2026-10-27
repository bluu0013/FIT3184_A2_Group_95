# Aussie EcoGuard: Friends & Foes

Multi-cloud serverless platform (FIT3184 2026 S2, Assignment 2). Users sign in, upload photos and
videos, the system tags invasive pests and pets with a pre-trained model, and everything can be
searched by tag, by example file, by thumbnail URL, by lost-pet details or through a Lex chatbot.

**Due: Monday 2 November 2026, 23:55.** Demo over Zoom is mandatory.

## Architecture

| Concern | Cloud | Service |
|---|---|---|
| Sign-up, sign-in | AWS | Cognito (hosted UI) |
| API | AWS | API Gateway HTTP API with Cognito JWT authorizer |
| Media storage | AWS | S3 (private, presigned URLs) |
| Metadata | AWS | DynamoDB |
| Event fan-out | AWS | S3 to EventBridge to Lambda |
| Chatbot | AWS | Lex V2 + fulfilment Lambda |
| Alerts | AWS | SNS with tag filter policies |
| ML inference, video frames | GCP | Cloud Run (FastAPI + Ultralytics YOLO + OpenCV) |
| Model weights and config | GCP | Cloud Storage (optional, local file works too) |

```mermaid
flowchart LR
  U[Browser] -->|hosted UI| COG[Cognito]
  U -->|ID token| APIGW[API Gateway]
  APIGW --> UP[upload_init]
  APIGW --> SR[search]
  APIGW --> MG[manage]
  APIGW --> CH[chat] --> LEX[Lex] --> LF[lex_fulfilment]
  U -->|presigned PUT| S3[(S3)]
  S3 -->|Object Created| EB[EventBridge]
  EB --> TH[thumbnail]
  EB --> IN[ingest]
  IN -->|presigned GET + key or JWT| RUN[Cloud Run inference]
  SR -->|user JWT| RUN
  IN --> DDB[(DynamoDB)]
  IN --> SNS[SNS alerts]
```

Why these choices are made and what they cost: [docs/decisions.md](docs/decisions.md). The full
architecture diagram (official AWS icons, editable in draw.io) and its numbered flows are in
[docs/architecture.md](docs/architecture.md).

## Repo layout

```
template.yaml                  AWS SAM template (everything on AWS)
services/aws/layers/common/    shared Python package used by every Lambda (tags, urls, db, storage)
services/aws/functions/        one folder per Lambda
services/gcp/inference/        Cloud Run service (detector, video frames, auth)
frontend/                      static web app (vanilla JS, Cognito hosted UI)
docs/                          API contract, data model, decisions, Lex bot spec
scripts/                       seed data helper
tests/                         unit tests for the pure logic
```

## Who owns what (change names as you agree)

The team splits by platform so each person works in one cloud toolchain.

| Member | Platform | Owns | Folders |
|---|---|---|---|
| A | AWS platform and pipeline | Cognito, API Gateway, IAM, S3, EventBridge, DynamoDB, SNS, upload, dedup, thumbnails, ingest, the call to GCP | `template.yaml`, `services/aws/functions/{upload_init,thumbnail,ingest,subscriptions}` |
| B | GCP and web UI | Inference service, model config, video frames, token check, and the whole web UI | `services/gcp/inference`, `frontend/` |
| C | AWS application logic | Tag, thumbnail, file and lost-pet search, bulk tag edit, delete, Lex bot and fulfilment | `services/aws/functions/{search,manage,chat,lex_fulfilment}`, `docs/lex-bot.md` |

Shared and agreed together: `docs/api-contract.md`, `docs/data-model.md`, `services/aws/layers/common`.
Change a contract in a PR that all three review.

**Hand-offs between members**

| From | To | What |
|---|---|---|
| A | B, C | Deployed stack and outputs (API URL, pool and client IDs). Target: within 3 days |
| A | B | The shared key (set as `INFERENCE_API_KEY` on Cloud Run) and the Cognito pool/client IDs for the Cloud Run auth |
| B | A | Cloud Run URL and a working `/detect` |
| C | B | Stable search, manage and chat routes (or agreed mock responses) |
| A, C | each other | `ecoguard_common` and DynamoDB fields. Both review any change |

**AWS Academy note:** Learner Lab accounts are per person. A owns the shared integration stack. C
deploys a personal stack for development and uses `scripts/seed_dummy_data.py`.

## Setup

Prerequisites: Python 3.12, AWS SAM CLI, Docker Desktop (Windows builds need `--use-container`),
Google Cloud CLI, an AWS account (Academy or personal) and a GCP project with billing or credits.

```bash
python -m venv .venv
.venv\Scripts\activate          # PowerShell; use source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

1. **Deploy inference to GCP first** (AWS needs its URL). See
   [services/gcp/inference/README.md](services/gcp/inference/README.md).
2. **Deploy AWS:**
   ```bash
   sam build --use-container
   sam deploy --guided
   ```
   Parameters you will be asked for: `CognitoDomainPrefix` (globally unique; letters, digits and
   hyphens only, not an ARN), `InferenceUrl`, `LabRoleArn` (Academy only, leave empty otherwise),
   `FrontendOrigin`, `InferenceApiKeyParam` (keep the default).

   The shared key lives in SSM Parameter Store, not in the stack. Create it once before the first
   deploy (or any time before ingest runs) and give the same value to Cloud Run:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   aws ssm put-parameter --name /ecoguard/inference-api-key --type SecureString --value "<the key>" --region <aws-region>
   ```
3. **Frontend:** copy the stack outputs into `frontend/js/config.js`, then
   ```bash
   cd frontend
   python -m http.server 5500
   ```
   Open http://localhost:5500. Cognito only allows `http` callbacks on localhost, so demo from there
   unless you put the site behind HTTPS.
4. **Lex bot:** follow [docs/lex-bot.md](docs/lex-bot.md), then redeploy with `LexBotId` and `LexBotAliasId`.
5. **Fake data for early query work:**
   ```bash
   python scripts/seed_dummy_data.py --table <TableName output>
   ```

## Status of this scaffold

Written but **not yet deployed or run against real AWS/GCP**. The pure logic (tag matching, URL
parsing, tag editing, frame sampling) has unit tests that pass. Everything else needs a first real
deployment and will have small fixes.

Known gaps to close (also tracked in the team board):

- [ ] Choose and verify a model that actually detects fox, feral pig, cane toad, rabbit (see decisions, ADR 5).
- [x] Shared inference key is read from SSM Parameter Store at runtime (no key in the stack or in git).
- [ ] Least-privilege IAM review (rubric 1.3). On Academy the `LabRole` is used instead.
- [ ] Lost-pet matching beyond species plus manual tags (colour, breed).
- [ ] Frontend polish: error states, loading states, responsive gallery.
- [ ] Keep one Cloud Run instance warm for the demo (HTTP API integrations time out at 30 s).

## Working agreement

See [CONTRIBUTING.md](CONTRIBUTING.md). Everyone commits their own work; commit history is part of
the marking evidence.
