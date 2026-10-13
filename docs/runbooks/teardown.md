# Runbook: teardown

Remove the resources in reverse order of creation so nothing keeps triggering work. The stack costs nothing when idle, but tearing it down removes the stored communications data and the IAM surface.

1. **EventBridge → Rules →** `comms-triage-inbound` → Disable, then Delete.
2. **Step Functions →** `comms-triage` → Delete (wait for running executions to finish).
3. **CloudWatch → Alarms →** delete the `ExecutionsFailed` alarm, if created.
4. **Lambda →** delete `comms-triage-reader` and `comms-triage-decider`.
5. **CloudWatch → Log groups →** delete `/aws/lambda/comms-triage-reader` and `/aws/lambda/comms-triage-decider`.
6. **DynamoDB →** `comms-triage-cases` → export to S3 first if you want to keep the records, then Delete.
7. **SNS →** delete the subscription, then the topic `comms-triage-analyst-alerts`.
8. **S3 →** `${BucketName}` → Empty, then Delete.
9. **IAM → Roles →** delete `comms-triage-reader-role`, `comms-triage-decider-role`, `comms-triage-statemachine-role` and the EventBridge target role the console created.
10. **Bedrock → Guardrails →** delete `comms-triage-prompt-attack`, if created.
11. Keep the budget alert in place.

Check that it worked: **Billing → Bills** should show no new charges on the following day, apart from small residual metering.
