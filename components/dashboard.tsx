"use client";

import { useEffect, useMemo, useState } from "react";
import { buildConversationFromTranscript, useCaseSamples } from "@/lib/triage/examples";
import { conversationSchema } from "@/lib/triage/types";

type ApiResult = {
  decision: {
    conversationId: string;
    disposition: string;
    reasons: string[];
  };
  usage: { inputTokens: number; outputTokens: number };
  estimatedCostUsd: number;
  remainingRunsThisHour: number;
  reader: { modelId: string; promptVersion: string };
};

export function Dashboard() {
  const defaultExample = useCaseSamples[0];
  const [selectedExampleId, setSelectedExampleId] = useState(defaultExample.id);
  const [transcript, setTranscript] = useState(defaultExample.transcript);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ApiResult | null>(null);

  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [debugCode, setDebugCode] = useState<string | null>(null);

  const selectedExample = useMemo(
    () => useCaseSamples.find((item) => item.id === selectedExampleId) ?? defaultExample,
    [defaultExample, selectedExampleId],
  );

  useEffect(() => {
    void fetch("/api/session/me")
      .then((res) => res.json())
      .then((json) => setSessionEmail(json.email ?? null))
      .catch(() => setSessionEmail(null));
  }, []);

  async function requestCode() {
    setError(null);
    const response = await fetch("/api/session/request-code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setError(payload.error ?? "Failed to send code.");
      return;
    }
    setDebugCode(payload.debugCode ?? null);
  }

  async function verifyCode() {
    setError(null);
    const response = await fetch("/api/session/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, code }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setError(payload.error ?? "Failed to verify code.");
      return;
    }
    setSessionEmail(payload.email);
    setDebugCode(null);
    setCode("");
  }

  async function logout() {
    await fetch("/api/session/logout", { method: "POST" });
    setSessionEmail(null);
    setResult(null);
  }

  async function runTriage() {
    setError(null);
    setResult(null);
    setIsLoading(true);
    try {
      const conversation = buildConversationFromTranscript(transcript);
      const validated = conversationSchema.parse(conversation);
      const response = await fetch("/api/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation: validated }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error ?? "Failed to triage conversation");
      }
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="container grid">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>Agents Under Audit</h1>
        {sessionEmail ? <button onClick={logout}>Sign Out ({sessionEmail})</button> : null}
      </div>

      <p className="muted" style={{ marginTop: 0 }}>
        Pick a sample chat or paste your own short transcript. The app extracts findings with
        Bedrock and decides <code>close</code>, <code>escalate</code>, or{" "}
        <code>human_review</code> in deterministic code.
      </p>

      {!sessionEmail ? (
        <div className="card grid">
          <strong>Sign in with email</strong>
          <p className="muted" style={{ margin: 0 }}>
            Enter your email, get a one-time code, then run triage.
          </p>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            style={{ padding: "0.6rem", borderRadius: 10, border: "1px solid #33415f" }}
          />
          <div className="row">
            <button onClick={requestCode}>Send Code</button>
          </div>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="6-digit code"
            style={{ padding: "0.6rem", borderRadius: 10, border: "1px solid #33415f" }}
          />
          <div className="row">
            <button className="primary" onClick={verifyCode}>
              Verify and Continue
            </button>
          </div>
          {debugCode ? (
            <p className="muted" style={{ margin: 0 }}>
              Debug code (Resend not configured): <code>{debugCode}</code>
            </p>
          ) : null}
        </div>
      ) : null}

      {sessionEmail ? (
        <>
          <div className="card grid">
            <strong>Examples</strong>
            <div className="row">
              {useCaseSamples.map((example) => (
                <button
                  key={example.id}
                  onClick={() => {
                    setSelectedExampleId(example.id);
                    setTranscript(example.transcript);
                  }}
                >
                  {example.title} (expected {example.expected})
                </button>
              ))}
            </div>
            <p className="muted" style={{ margin: 0 }}>
              Selected: {selectedExample.title}
            </p>
          </div>

          <div className="card grid">
            <strong>Transcript</strong>
            <p className="muted" style={{ margin: 0 }}>
              Format each line as <code>Sender: message</code>. Keep it concise.
            </p>
            <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} />
            <div className="row">
              <button className="primary" onClick={runTriage} disabled={isLoading}>
                {isLoading ? "Running..." : "Run Triage"}
              </button>
            </div>
          </div>
        </>
      ) : null}

      {error ? <p style={{ color: "#ff8f8f", margin: 0 }}>{error}</p> : null}

      {result ? (
        <div className="card grid">
          <strong>Result</strong>
          <p style={{ margin: 0 }}>
            Disposition: <b>{result.decision.disposition}</b>
          </p>
          <p className="muted" style={{ margin: 0 }}>
            Conversation: {result.decision.conversationId} | Remaining runs this hour:{" "}
            {result.remainingRunsThisHour}
          </p>
          <div>
            <strong>Reasons</strong>
            <ul>
              {result.decision.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
          <p className="muted" style={{ margin: 0 }}>
            Tokens in/out: {result.usage.inputTokens}/{result.usage.outputTokens} | Estimated
            cost: ${result.estimatedCostUsd.toFixed(6)}
          </p>
          <p className="muted" style={{ margin: 0 }}>
            Model: {result.reader.modelId} | Prompt: {result.reader.promptVersion}
          </p>
        </div>
      ) : null}
    </div>
  );
}
