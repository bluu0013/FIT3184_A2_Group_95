# Architecture diagram

Source: [architecture.drawio](architecture.drawio). Open it at https://app.diagrams.net (File, Open from
Device) or with the VS Code "Draw.io Integration" extension. It uses draw.io's built-in AWS shapes, which
are the official AWS Architecture Icons. Export a PNG or SVG (File, Export as) for the report.

Colours: AWS service icons follow the AWS category colours. Red thick arrows are the two cross-cloud
calls from AWS to GCP. The GCP boxes are drawn as plain shapes (no GCP icon library is used).

## What the numbers on the diagram mean

| # | Flow | Services |
|---|---|---|
| 1 | The browser signs the user up or in on the Cognito hosted UI and receives tokens. | Cognito |
| 2 | Every API call carries the ID token. API Gateway's JWT authorizer validates it against the user pool, so signed-out callers get 401. | API Gateway, Cognito |
| 3 | `upload_init` checks the SHA-256 for a duplicate with a conditional write, then returns a presigned PUT URL. The browser uploads straight to S3. | `upload_init`, DynamoDB, S3 |
| 4 | S3 emits Object Created for `media/`. EventBridge fans out to two Lambdas: `thumbnail` (resize and compress to `thumbs/`) and `ingest`. | S3, EventBridge, Lambda |
| 5 | `ingest` re-hashes the stored object (rejects a mismatch), gets tags from GCP, and writes tags, status and metadata. | `ingest`, DynamoDB |
| 6 | `ingest` publishes the species tags. SNS filter policies deliver the email only to subscribers of those tags. | `ingest`, SNS |
| 7 | **Cross-cloud call (S3-triggered):** `ingest` sends a presigned S3 URL and the shared `X-Api-Key` (read from SSM Parameter Store) to Cloud Run `/detect`. | `ingest`, SSM, Cloud Run |
| 8 | **Cross-cloud call (user-triggered):** `/search/by-file` and `/search/lost-pet` forward the user's Cognito JWT, which Cloud Run verifies against the pool's JWKS. The image is never stored. | `search`, Cloud Run |

Not numbered: `chat` relays text to Lex V2, whose fulfilment Lambda queries DynamoDB and returns
presigned links. `subscriptions` registers a tag filter on the SNS topic. `manage` edits tags and
deletes files, records and thumbnails together.

## Why each service sits where it does

| Service | Cloud | Reason |
|---|---|---|
| Cognito | AWS | Required by the spec, and it issues the JWTs that both clouds verify. |
| API Gateway (HTTP API) | AWS | Built-in Cognito JWT authorizer on every route, cheap and low latency. |
| Lambda | AWS | Serverless glue with no servers to run; one shared layer keeps logic identical across functions. |
| S3 | AWS | Private object store. Presigned URLs let the browser upload and view without exposing the bucket. |
| EventBridge | AWS | S3 cannot send overlapping prefix events to two targets, so EventBridge fans out to `thumbnail` and `ingest`. |
| DynamoDB | AWS | Pay-per-request metadata store. The SHA-256 primary key makes dedup a single conditional write. |
| SNS | AWS | Email alerts with per-subscriber tag filter policies, no polling. |
| Lex V2 | AWS | Required chatbot, with a fulfilment Lambda that reuses the search code. |
| SSM Parameter Store | AWS | Holds the shared Cloud Run key outside code, stack parameters and git. |
| Cloud Run | GCP | Runs a container, so PyTorch, Ultralytics and OpenCV fit without Lambda's package limit; CPU and memory sized per instance. |
| Cloud Storage | GCP | Optional home for model weights and the model config, so a new model needs no code change. |

Trade-offs of the two-cloud split are in [decisions.md](decisions.md) (ADRs 1 and 7): extra latency and
egress, two sets of credentials, and a 30 s HTTP API timeout that a cold ML container can exceed, which
is why one Cloud Run instance stays warm during the demo.
