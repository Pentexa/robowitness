import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RoboWitness — Robot Test Programı",
  description:
    "Robot düzeltmelerini bilgisayarda test eden program: robotu çalıştırın, hatayı inceleyin, yeni ayarları deneyin ve bağımsız sonucu görün.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
