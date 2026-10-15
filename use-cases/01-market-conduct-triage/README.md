# Use Case 01: Market Conduct Alert Triage

This scenario demonstrates a hardened control boundary: untrusted employee chat text can influence findings, but cannot directly set the final verdict.

## Architecture Diagram

```mermaid
flowchart LR
  Visitor[Visitor]
  Dashboard[VercelDashboard]
  TriageApi[TriageApi]
  Prescreen[PrescreenRules]
  Reader[BedrockReaderNoTools]
  Decider[DeterministicPolicy]
  Mail[ResendEmailAlerts]
  Store[CaseStoreOptional]

  Visitor --> Dashboard
  Dashboard --> TriageApi
  TriageApi --> Prescreen
  TriageApi --> Reader
  TriageApi --> Decider
  Decider --> Store
  Decider --> Mail
  Decider --> Dashboard
```

## Flow Diagram

```mermaid
flowchart TD
  Start[UserSignsInAndRunsChat]
  Parse[ParseAndValidateConversation]
  Rules[RunPrescreenRules]
  Model[RunBedrockReader]
  Policy[ApplyDeterministicPolicy]
  Decide{"DispositionClose"}
  Save[SaveCaseRecord]
  Send[SendEmailAlert]
  EndClose[ReturnCloseResult]
  EndAlert[ReturnEscalateOrReviewResult]

  Start --> Parse --> Rules --> Model --> Policy --> Save --> Decide
  Decide -->|yes| EndClose
  Decide -->|no| Send --> EndAlert
```

## Why This Use Case Matters

- AI-directed instructions in chat are detected and escalated.
- Final decision is policy-driven code, not model free text.
- Alert email excludes raw transcript content.
