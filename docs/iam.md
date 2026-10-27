# IAM roles and permissions

Rubric 1.3 asks for least privilege with no wildcards. On a personal AWS account SAM creates one role
per Lambda from the `Policies` in `template.yaml`. On AWS Academy, `LabRoleArn` is passed and every
function uses `LabRole` instead (Academy does not allow creating roles), so the table below is what
each function is *designed* to need, and what the template grants when it can.

| Function | S3 | DynamoDB | Other |
|---|---|---|---|
| `upload_init` | `PutObject`, `GetObject` on `media/*` (signs the presigned PUT and the duplicate GET) | `PutItem`, `GetItem` | |
| `thumbnail` | `GetObject` on `media/*`, `PutObject` on `thumbs/*` | `GetItem`, `UpdateItem` | |
| `ingest` | `GetObject`, `DeleteObject` on `media/*` (hash check, presigned GET for Cloud Run, reject on mismatch) | `GetItem`, `UpdateItem` | `sns:Publish` on the alerts topic, `ssm:GetParameter` on the one inference-key parameter |
| `subscriptions` | | | `sns:Subscribe` on the alerts topic |
| `chat` | | | `lex:RecognizeText` on the one bot alias (`LexBotId`/`LexBotAliasId`) |
| `search`, `lex_fulfilment` | read the bucket (SAM `S3ReadPolicy`) | read the table (SAM `DynamoDBReadPolicy`) | |
| `manage` | SAM `S3CrudPolicy` on the bucket | SAM `DynamoDBCrudPolicy` on the table | `sns:Publish` on the alerts topic |

Notes

- Every statement names a bucket, table or topic ARN. The only `*` is the CORS `AllowedHeaders` on
  the bucket, which is not an IAM policy.
- Nothing grants `s3:*`, `dynamodb:*` or `Resource: "*"`.
- Cloud Run is called with a Cognito token (user requests) or the shared `X-Api-Key` (S3-triggered
  ingest). The key is an SSM SecureString read by `ingest` at runtime, so it is not in the template,
  the stack parameters, the Lambda environment or git. Cognito pool and client IDs are not secrets.
- The API Gateway authorizer is the HTTP API JWT authorizer, set as the default so every route
  requires a valid Cognito token.
