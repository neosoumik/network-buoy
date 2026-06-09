import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Network Buoy — Threat Monitor",
  description: "Real-time honeypot attack visualization",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex flex-col bg-[#020814]">{children}</body>
    </html>
  );
}
