import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppProvider } from "../context/AppContext";
import UnitsToggle from "../components/UnitsToggle";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SkiRank — Global Ski Resort Rankings",
  description:
    "Daily-updated rankings of ski resorts worldwide based on real snow and weather conditions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 min-h-screen`}>
        <AppProvider>
          <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
            <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
              <a href="/" className="text-xl font-bold text-blue-600 tracking-tight">
                SkiRank
              </a>
              <nav className="flex items-center gap-5 text-sm text-slate-600">
                <a href="/rankings" className="hover:text-blue-600 transition-colors">
                  Rankings
                </a>
                <a href="/map" className="hover:text-blue-600 transition-colors">
                  Map
                </a>
                <a href="/about" className="hover:text-blue-600 transition-colors">
                  About
                </a>
                <UnitsToggle />
              </nav>
            </div>
          </header>
          <main>{children}</main>
        </AppProvider>
      </body>
    </html>
  );
}
