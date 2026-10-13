# Runbook: AWS console setup

Deploys the stack described in the [design document](../design.md) by hand in the AWS console. Region: **us-east-1** (substitute your own consistently). Allow 60–90 minutes.

Placeholders used in `infra/` and below: `${AccountId}`, `${Region}`, `${BucketName}`, `${ReaderFunctionArn}`, `${DeciderFunctionArn}`, `${CasesTableName}` and `${AnalystTopicArn}`. A suggested bucket name is `comms-triage-<account id>-use1`.

Steps marked **Cost** are the ones that keep the bill near zero. Don't skip them.

## 0. Guard the bill first

1. **Cost.** **Billing and Cost Management → Budgets → Create budget → Cost budget**: $5 per month, with alerts at **$1 actual** and **$5 forecasted** to your email.
2. **Billing → Credits**: note which services your credits cover and when they expire.

## 1. Bedrock model access

1. **Amazon Bedrock → Model catalog → Amazon Nova Lite.** Open it in the playground and send one short test prompt. If the console asks you to request access, request it for Nova Lite.
2. If on-demand invocation is not offered in your region, use the inference profile ID `us.amazon.nova-lite-v1:0` wherever this runbook says `amazon.nova-lite-v1:0`.
3. **Cost.** Leave **Settings → Model invocation logging** off. It would copy every transcript into another store.

## 2. Validate locally before deploying anything

```bash
aws configure sso --profile comms-triage     # or any named profile with Bedrock access
cp .env.example .env
uv run --env-file .env triage run CHAT-012                   # ~$0.00007
uv run --env-file .env triage eval --pipeline all            # ~$0.0024
```

Keep the two reports in `outputs/eval/`. They are the baseline the deployed stack must match.

## 3. Optional: Guardrail with a prompt-attack filter

**Cost.** This costs about $0.15 per 1,000 text units, which is more per conversation than the model. Create it for a comparison run, then delete it.

1. **Bedrock → Guardrails → Create guardrail**, named `comms-triage-prompt-attack`.
2. Content filters: enable **Prompt attacks** at **High**. Leave the harmful-content categories off, because trader language trips them without adding signal.
3. Skip denied topics, word filters and PII. Create the guardrail, then **Create version**.
4. Set `BEDROCK_GUARDRAIL_ID` and `BEDROCK_GUARDRAIL_VERSION` in `.env`, re-run `triage eval --pipeline quarantined`, and compare the hard-negative false positives against step 2.

## 4. S3 bucket

1. **S3 → Create bucket** `${BucketName}`. Keep **Block all public access** on, **Bucket Versioning** off, and default encryption at **SSE-S3**. **Cost:** SSE-KMS with a customer-managed key adds a monthly charge.
2. **Permissions → Bucket policy**: paste [`infra/iam/bucket-policy.json`](../../infra/iam/bucket-policy.json) with `${BucketName}` replaced. It denies any request that doesn't use TLS.
3. **Properties → Amazon EventBridge → Edit → On.**
4. **Cost.** **Management → Create lifecycle rule**: prefix `inbound/`, expire current versions after **7 days**.

## 5. DynamoDB table

**DynamoDB → Create table**:

- Table name: `comms-triage-cases`
- Partition key: `conversation_id` (String)
- Sort key: `decided_at` (String)
- Table settings: **Customize**, capacity mode **On-demand**. **Cost:** leave point-in-time recovery off for this environment.

## 6. SNS topic

1. **SNS → Topics → Create topic**: Standard, named `comms-triage-analyst-alerts`.
2. **Create subscription**: protocol Email, your address. Confirm it from your inbox.

## 7. IAM roles for the Lambdas

1. **IAM → Roles → Create role**, trusted entity **Lambda**, name `comms-triage-reader-role`.
   - Attach `AWSLambdaBasicExecutionRole`.
   - Add an inline policy from [`infra/iam/reader-lambda-policy.json`](../../infra/iam/reader-lambda-policy.json) with the placeholders replaced. Remove the guardrail statement if you skipped step 3.
2. Create a second Lambda role, `comms-triage-decider-role`, with `AWSLambdaBasicExecutionRole` only.

## 8. Lambda functions

Build the package locally:

```bash
scripts/build_lambda.sh            # writes dist/comms-triage-lambda.zip for arm64
```

**Lambda → Create function → Author from scratch**, twice:

| Setting | Reader | Decider |
| --- | --- | --- |
| Name | `comms-triage-reader` | `comms-triage-decider` |
| Runtime and architecture | Python 3.12, **arm64** | Python 3.12, **arm64** |
| Role | `comms-triage-reader-role` | `comms-triage-decider-role` |
| Handler | `comms_triage.lambda_handlers.read_handler` | `comms_triage.lambda_handlers.decide_handler` |
| Memory / timeout | 256 MB / 3 min | 128 MB / 10 s |
| Environment | `BEDROCK_MODEL_ID=amazon.nova-lite-v1:0`, plus guardrail variables if used | none |

For each function:

1. **Code → Upload from → .zip file**: `dist/comms-triage-lambda.zip`.
2. **Runtime settings → Edit**: set the handler.
3. **Cost.** **Configuration → Monitoring and operations tools**: leave X-Ray tracing off. Open the function's CloudWatch log group (it appears after the first invocation) and set **retention to 7 days**.

**Cost.** On the reader only, set **Configuration → Concurrency → Reserved concurrency** to **5**. If the console refuses because the account's concurrency limit is 10 (common on new accounts), skip this step; that account limit already caps the reader.

## 9. State machine

1. **IAM → Roles → Create role**, trusted entity **Step Functions**, name `comms-triage-statemachine-role`. Add an inline policy from [`infra/iam/statemachine-policy.json`](../../infra/iam/statemachine-policy.json) with the placeholders replaced.
2. **Step Functions → Create state machine → Blank**, type **Standard**, name `comms-triage`.
3. Open **Code**, paste [`infra/statemachine.asl.json`](../../infra/statemachine.asl.json) and replace:
   - `${ReaderFunctionArn}` and `${DeciderFunctionArn}` with the function ARNs from step 8
   - `${CasesTableName}` with `comms-triage-cases`
   - `${AnalystTopicArn}` with the topic ARN from step 6
4. **Config → Permissions**: choose `comms-triage-statemachine-role`.
5. **Cost.** **Logging**: **OFF**. Execution history is kept for 90 days at no charge.

## 10. EventBridge rule

1. **EventBridge → Rules → Create rule**: name `comms-triage-inbound`, default bus, **Rule with an event pattern**.
2. Choose a custom pattern and paste [`infra/eventbridge-rule.json`](../../infra/eventbridge-rule.json) with `${BucketName}` replaced. The pattern only matches `inbound/*.json`, so creating the folder doesn't start a run.
3. Target: **Step Functions state machine** `comms-triage`, and let the console create a role for this target.

## 11. Optional: failure alarm

**CloudWatch → Alarms → Create alarm** on the metric `AWS/States ExecutionsFailed` for `comms-triage`: Sum ≥ 1 over 5 minutes, notifying `comms-triage-analyst-alerts`. The first 10 alarms in an account are free.

## 12. Smoke test

```bash
uv run triage export               # writes build/inbound/CHAT-*.json, without labels
```

1. In the S3 console, create the folder `inbound/` and upload `CHAT-012.json`.
2. **Step Functions → comms-triage → Executions**: the run should pass through `ClaimEvent → ReadConversation → Decide → RecordCase → NotifyAnalyst`.
3. **DynamoDB → Explore items**: a `case` item with `disposition = escalate` and prescreen reasons, plus an `event_claim` item.
4. Check that an email alert arrived. It contains IDs and reasons only, no chat text.
5. Upload `CHAT-001.json`. It should end at `Closed` with no email.
6. Upload the remaining files and compare the dispositions with your local `quarantined` report from step 2. Expect about five escalation emails.
7. Check **Billing → Bills** the next day. Model cost should show as fractions of a cent.

When you are done, follow [`teardown.md`](teardown.md).
