import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agents Under Audit Demo",
  description: "Prompt-injection-resistant chat triage on AWS Bedrock.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
