import type { Metadata } from "next";

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
          {children}
        </Auth0Provider>
      </body>
    </html>
  );
}
