import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RoboWitness — Independent Verification for AI Robotics Fixes",
  description: "Locally runnable verification platform ensuring AI-proposed policy fixes survive reproducible simulation gates.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
