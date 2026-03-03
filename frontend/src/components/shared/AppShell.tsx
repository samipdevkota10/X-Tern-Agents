"use client";

import * as React from "react";
import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/shared/Sidebar";
import { Navbar } from "@/components/shared/Navbar";

export function AppShell(props: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  if (isLogin) {
    return <>{props.children}</>;
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <Navbar />
      <main className="ml-60 pt-14 p-6 min-h-screen">{props.children}</main>
    </div>
  );
}

