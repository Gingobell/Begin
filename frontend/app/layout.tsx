import type { Metadata } from "next";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Begin · 你的日记伙伴",
  description: "FortuneDiary — AI diary companion with fortune insights",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <CopilotKit
          runtimeUrl="/api/copilotkit"
          agent="fortune_diary"
          properties={{
            // TODO: replace with real auth user_id
            user_id: "11111111-1111-1111-1111-111111111111",
          }}
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
