# Design decisions

Short records of what the scaffold assumes. Change them if the team disagrees, but update this file
because the demo asks us to justify each service.

## 1. AWS primary, GCP for ML inference

- **Why AWS primary:** Cognito and Lex are mandatory, and S3 + Lambda + DynamoDB + SNS keep the data
  plane in one place.
- **Why GCP for ML:** Cloud Run runs a container, so Ultralytics, PyTorch and OpenCV fit without
  fighting Lambda's 250 MB package limit, and CPU/RAM can be sized per request. GCP free credits also
  spread cost across two budgets.
- **Costs:** cross-cloud latency and egress, two sets of credentials, and an HTTP API timeout of 30 s
  that a cold ML container can exceed. Mitigation: keep a Cloud Run instance warm during the demo.

## 2. Content-addressed keys

The file's SHA-256 is its identity. Dedup is a conditional `PutItem`, and any media or thumbnail URL
maps back to a record. The browser computes the hash; `ingest` re-hashes the stored object and
rejects a mismatch, so a client cannot lie about the checksum.

## 3. EventBridge fan-out instead of two S3 notifications

S3 does not allow two notification configurations with overlapping prefixes for the same event
type. Enabling EventBridge on the bucket lets `thumbnail` and `ingest` each get their own rule.

## 4. Model chosen by config, not code

The inference service reads `model_config.json` (local file or `gs://`) and reloads it when the
file's `model_version` or `weights` change, so a new model needs no Lambda or container change.
Supported types: `yolo` (any Ultralytics weights) and `yolo_world` (open-vocabulary, classes taken
from the config). The first model must be one of MegaDetector, Ultralytics YOLO or Rekognition, per
the spec.

## 5. Species coverage gap (needs an early check)

Stock COCO YOLO weights know `cat`, `dog`, `bird`, `horse`, `sheep`, `cow` and a few more, but **not**
fox, feral pig, rabbit or cane toad. The scaffold defaults to `yolo_world` with a species list so the
pipeline can be tested end to end. Before relying on it, check accuracy on a dozen real photos of each
target species. Fallbacks, in order of effort:

1. Rekognition `DetectLabels` as a second model for low-confidence results (allowed as a chain).
2. A Hugging Face YOLO or classifier trained on Australian fauna or camera-trap data, loaded through
   the same config.
3. MegaDetector for animal boxes plus a species classifier on the crops.

## 6. Search by file stays out of storage

`/search/by-file` takes the image as base64 in the JSON body and forwards it straight to inference.
It never touches S3 or DynamoDB, which is the strongest way to meet the privacy requirement. Cost:
images only, roughly 4 MB. If video search is needed, use a presigned `tmp/` upload with a lifecycle
rule and delete after use.

## 7. Cross-cloud authentication

- User-initiated calls (`/search/by-file`, `/search/lost-pet`): the user's Cognito token is forwarded
  and verified in Cloud Run against the pool's JWKS.
- S3-triggered ingest has no user token, so it sends a shared `X-Api-Key`. The key is an SSM
  Parameter Store SecureString (`/ecoguard/inference-api-key`), read by `ingest` and cached per
  container. Only the parameter's name is a stack parameter, so the key is never in the template,
  stack, Lambda environment or git. Rotating it means updating the SSM value and the Cloud Run env var.
- Cloud Run is deployed with `--allow-unauthenticated` because the caller is Lambda, not a Google
  principal. All authorisation happens in the application layer.

## 8. Private bucket, presigned URLs

Nothing is public. The API returns presigned GET URLs valid for one hour. On AWS Academy the
credentials rotate, so a very old presigned URL may stop working even before expiry; the API accepts
any previously issued URL for lookups because it only uses the path.

## 9. One shared Lambda layer

Tag logic, URL parsing and DynamoDB/S3 helpers live in `ecoguard_common` so the search Lambda and the
Lex fulfilment Lambda behave identically, and the pure parts are unit-tested without AWS.

## 10. Work split by platform

| Member | Platform | Share of marks (approx.) |
|---|---|---|
| A | AWS platform and pipeline | 27 |
| B | GCP, ML and web UI | 28 to 31 |
| C | AWS application logic | 30 |

Considered and rejected: a split by feature, where C carried about 40 marks (all queries, Lex,
tags, delete and two UIs) and A about 15. Platform ownership gives balanced work and one toolchain
per person. The cost is a higher bus factor and B's dependence on A and C, so we mitigate with a
deployed stack by day 3, mock data and seed script for the UI, week 2 cross-training, and
cross-platform PR reviews (see CONTRIBUTING.md).
