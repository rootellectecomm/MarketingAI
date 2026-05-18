"use client";

import { Bot } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";
import { useAuthStore } from "@/store/auth";

export default function LoginPage() {
  const router = useRouter();
  const setToken = useAuthStore((state) => state.setToken);
  const [email, setEmail] = useState("admin@rootellect.local");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState<string | null>(null);
  const [backendAdminEmail, setBackendAdminEmail] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--background)] px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--primary)] text-[var(--primary-foreground)]">
            <Bot size={20} />
          </div>
          <CardTitle>Rootellect AI</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-3"
            onSubmit={async (event) => {
              event.preventDefault();
              setError(null);
              setIsLoading(true);
              let adminEmail = backendAdminEmail;
              try {
                const bootstrap = await api.bootstrap();
                adminEmail = bootstrap.user.email;
                setBackendAdminEmail(adminEmail);
                const response = await api.login(email, password);
                setToken(response.access_token);
                router.push("/");
              } catch (err) {
                const message = err instanceof Error ? err.message : "Unable to sign in.";
                if (message.toLowerCase().includes("invalid credentials") && adminEmail) {
                  setError(`Invalid credentials. Backend admin email is ${adminEmail}. Use that email and the ADMIN_PASSWORD from backend Vercel env.`);
                } else {
                  setError(message);
                }
              } finally {
                setIsLoading(false);
              }
            }}
          >
            <Input type="email" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
            <Button className="w-full" type="submit" disabled={isLoading}>
              {isLoading ? "Signing in" : "Sign in"}
            </Button>
            <Button
              className="w-full"
              type="button"
              variant="secondary"
              disabled={isResetting || isLoading}
              onClick={async () => {
                setError(null);
                setIsResetting(true);
                try {
                  await api.resetAdmin();
                  const bootstrap = await api.bootstrap();
                  setEmail(bootstrap.user.email);
                  setBackendAdminEmail(bootstrap.user.email);
                  setError(`Admin reset. Use ${bootstrap.user.email} and the ADMIN_PASSWORD from backend Vercel env.`);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Admin reset failed.");
                } finally {
                  setIsResetting(false);
                }
              }}
            >
              {isResetting ? "Resetting admin" : "Reset admin from env"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
