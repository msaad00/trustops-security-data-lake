import type { Metadata } from "next";
import { ReactNode } from "react";
import { Toaster } from "sonner";
import { Providers } from "./providers";
import { Shell } from "@/components/shell/Shell";
import "./globals.css";

const DESCRIPTION =
  "Continuous compliance assessment for security data lakes — SOC 2, NIST AI RMF, and beyond.";

export const metadata: Metadata = {
  title: { default: "TrustOps Assessment Console", template: "%s · TrustOps" },
  description: DESCRIPTION,
  applicationName: "TrustOps",
  openGraph: {
    title: "TrustOps Assessment Console",
    description: DESCRIPTION,
    siteName: "TrustOps",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "TrustOps Assessment Console",
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <Shell>{children}</Shell>
        </Providers>
        <Toaster
          position="bottom-center"
          richColors
          closeButton
          toastOptions={{ duration: 4200 }}
        />
        <script
          id="app-data"
          type="application/json"
          // dashboard.py replaces this with the live assessment payload when
          // generating a static console.html for offline/audit distribution.
          dangerouslySetInnerHTML={{ __html: "{}" }}
        />
      </body>
    </html>
  );
}
