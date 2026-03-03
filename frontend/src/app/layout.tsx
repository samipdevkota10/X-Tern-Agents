import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "next-themes";

import "./globals.css";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/shared/AppShell";
import { AuthProvider } from "@/lib/auth";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DisruptIQ — Control Tower",
  description: "AI-native enterprise dashboard for disruption response planning.",
};

export default function RootLayout(props: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <TooltipProvider>
            <AuthProvider>
              <AppShell>{props.children}</AppShell>
              <Toaster
                position="bottom-right"
                toastOptions={{
                  classNames: {
                    toast: "glass-card border-white/10 bg-black/40 text-white shadow-xl",
                    title: "text-white",
                    description: "text-white/60",
                    actionButton:
                      "bg-cyan-400 text-slate-950 hover:bg-cyan-300",
                    cancelButton:
                      "bg-white/10 text-white hover:bg-white/15",
                  },
                }}
              />
            </AuthProvider>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
