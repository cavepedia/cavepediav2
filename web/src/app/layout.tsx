import type { Metadata } from "next";

import { CopilotKit } from "@copilotkit/react-core";
import { Auth0Provider } from "@auth0/nextjs-auth0/client";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

export const metadata: Metadata = {
  title: "Cavepedia",
  description: "The AI Cave Chat that nobody asked for.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={"antialiased"}>
        <Auth0Provider>
          <CopilotKit runtimeUrl="/api/copilotkit" agent="sample_agent" properties={{ streamMode: ["events"] }}>
            {children}
          </CopilotKit>
        </Auth0Provider>
      </body>
    </html>
  );
}
