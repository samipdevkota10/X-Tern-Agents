"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Page() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("disruptiq_token");
    router.replace(token ? "/dashboard" : "/login");
  }, [router]);

  return null;
}
