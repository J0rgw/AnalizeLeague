import type { Metadata } from "next";
import { Urbanist } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";

const urbanist = Urbanist({
  subsets: ["latin"],
  weight: ["600", "800"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AnalizeLeague",
  description: "AI assistant for League of Legends analysts and coaches",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={urbanist.variable}>
      <body>
        <div className="min-h-screen flex flex-col">
          <Nav />
          <main className="flex-1 pt-14">{children}</main>
        </div>
      </body>
    </html>
  );
}
