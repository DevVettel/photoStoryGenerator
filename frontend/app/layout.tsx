import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PhotoStory",
  description: "AI Video Generator",
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