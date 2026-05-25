import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";

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
    <html lang="en" suppressHydrationWarning>
      <body>
        <div className="min-h-screen flex flex-col">
          <Nav />
          <main className="flex-1 pt-14">{children}</main>
        </div>
      </body>
    </html>
  );
}
