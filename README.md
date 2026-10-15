# Agents Under Audit: Conduct Alert Triage

This project showcases a practical market-conduct triage use case: an untrusted employee chat is reviewed with Amazon Bedrock, and the final outcome is decided in deterministic code so chat text cannot directly force a verdict.

Live app URL: add your deployed Vercel URL here.

## What It Does

- Lets users sign in with email using a one-time code
- Runs triage on sample or custom chat transcripts
- Returns one outcome: `close`, `escalate`, or `human_review`
- Sends email alerts for `escalate` and `human_review` without including raw transcript text

## Use Case Diagrams

- [Use Case 01: Market Conduct Alert Triage](use-cases/01-market-conduct-triage/README.md)

## Local Run

```bash
npm install
cp .env.example .env.local
npm run dev
```

Then open `http://localhost:3000`.

## Environment Setup

- Configure session secret (`SESSION_SECRET`)
- Configure Bedrock access (`AWS_REGION`, `BEDROCK_MODEL_ID`)
- Configure Resend (`RESEND_API_KEY`, `ALERT_FROM_EMAIL`)
- Optional: configure `POSTGRES_URL` for case-record persistence

## Notes

- The chats and names are synthetic and fictional.
- This repository is a reference implementation, not a production surveillance platform.

## License

MIT. See `LICENSE`.
