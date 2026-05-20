"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/store/auth";

export function AuthHydrator() {
  const hydrate = useAuthStore((state) => state.hydrate);
  useEffect(() => {
    hydrate();
  }, [hydrate]);
  return null;
}
