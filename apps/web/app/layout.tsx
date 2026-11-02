import type { Metadata } from "next";
import "./globals.css";
import { LocaleProvider } from "../lib/i18n";

export const metadata: Metadata = {
  title: "RoboWitness — Robot Verification Console",
  description:
    "Verify AI-generated robot policy fixes in simulation: run the baseline, inspect the failure, try the fix, and see the independently measured, sealed verdict.",
  icons: { icon: "/rw-mark.svg" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
