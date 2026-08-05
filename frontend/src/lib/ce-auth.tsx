"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  CEUser,
  ceApi,
  clearCESession,
  getCEToken,
  loginWithCredentials,
  setCESession,
} from "@/lib/ce-api";

type SessionContextValue = {
  user: CEUser | null;
  isLoading: boolean;
  signIn: (
    username: string,
    password: string,
    options?: { totpCode?: string; recoveryCode?: string },
  ) => Promise<void>;
  signOut: () => void;
  refreshUser: () => Promise<void>;
};

const SessionContext = React.createContext<SessionContextValue | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = React.useState<CEUser | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    const bootstrap = async () => {
      const token = getCEToken();

      if (token) {
        try {
          const response = await ceApi("/api/auth/me");
          if (response.ok) {
            const payload = (await response.json()) as { user?: CEUser };
            if (payload.user) {
              setCESession(token, payload.user);
              setUser(payload.user);
              setIsLoading(false);
              return;
            }
          }
        } catch {
          // Backend offline; fall through to session reset.
        }
        clearCESession();
        setUser(null);
        setIsLoading(false);
        return;
      }

      try {
        const configResponse = await ceApi("/api/auth/config");
        if (configResponse.ok) {
          const config = (await configResponse.json()) as { auth_enabled?: boolean };
          if (!config.auth_enabled) {
            const meResponse = await ceApi("/api/auth/me");
            if (meResponse.ok) {
              const payload = (await meResponse.json()) as { user?: CEUser };
              if (payload.user) {
                setUser(payload.user);
                setIsLoading(false);
                return;
              }
            }
          }
        }
      } catch {
        // Backend offline; unauthenticated bootstrap is expected on the login page.
      }

      setUser(null);
      setIsLoading(false);
    };
    void bootstrap();
  }, []);

  const signIn = React.useCallback(
    async (
      username: string,
      password: string,
      options?: { totpCode?: string; recoveryCode?: string },
    ) => {
      const nextUser = await loginWithCredentials(username, password, options);
      setUser(nextUser);
    },
    [],
  );

  const refreshUser = React.useCallback(async () => {
    const token = getCEToken();
    if (!token) {
      setUser(null);
      return;
    }
    const response = await ceApi("/api/auth/me");
    if (!response.ok) {
      return;
    }
    const payload = (await response.json()) as { user?: CEUser };
    if (payload.user) {
      setCESession(token, payload.user);
      setUser(payload.user);
    }
  }, []);

  const signOut = React.useCallback(() => {
    clearCESession();
    setUser(null);
    router.push("/login");
  }, [router]);

  const value = React.useMemo(
    () => ({ user, isLoading, signIn, signOut, refreshUser }),
    [user, isLoading, signIn, signOut, refreshUser],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useCESession(): SessionContextValue {
  const ctx = React.useContext(SessionContext);
  if (!ctx) {
    throw new Error("useCESession must be used within SessionProvider");
  }
  return ctx;
}

export function useRequireSession(): SessionContextValue & { user: CEUser } {
  const session = useCESession();
  const router = useRouter();

  React.useEffect(() => {
    if (!session.isLoading && !session.user && !getCEToken()) {
      router.replace("/login");
    }
  }, [session.isLoading, session.user, router]);

  return session as SessionContextValue & { user: CEUser };
}

export function useRequireAdmin(): SessionContextValue & { user: CEUser; isAdmin: boolean } {
  const session = useRequireSession();
  const router = useRouter();
  const isAdmin =
    session.user?.role === "admin" ||
    session.user?.role === "owner" ||
    session.user?.role === "developer";

  React.useEffect(() => {
    if (!session.isLoading && session.user && !isAdmin) {
      router.replace("/usage");
    }
  }, [session.isLoading, session.user, isAdmin, router]);

  return { ...session, isAdmin };
}

export { getCEToken, getCEUser, clearCESession, setCESession } from "@/lib/ce-api";
