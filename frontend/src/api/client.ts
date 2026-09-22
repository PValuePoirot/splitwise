// Typed API client with JWT auth and automatic token refresh.
import type {
  Expense,
  Group,
  GroupBalances,
  GroupDetail,
  Settlement,
  TokenPair,
  User,
} from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let refreshPromise: Promise<string> | null = null;

const TOKEN_KEY = "splitwise_refresh_token";

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem(TOKEN_KEY, refresh);
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem(TOKEN_KEY);
}

export function hasStoredSession(): boolean {
  return !!localStorage.getItem(TOKEN_KEY);
}

export function getAccessToken(): string | null {
  return accessToken;
}

async function refreshAccess(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  if (!refreshToken) throw new Error("No refresh token");
  refreshPromise = doRefresh().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

async function doRefresh(): Promise<string> {
  const resp = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!resp.ok) {
    clearTokens();
    throw new Error("Session expired");
  }
  const data: TokenPair = await resp.json();
  accessToken = data.access_token;
  refreshToken = data.refresh_token;
  localStorage.setItem(TOKEN_KEY, refreshToken!);
  return accessToken!;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  let resp = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (resp.status === 401 && refreshToken) {
    try {
      const newToken = await refreshAccess();
      headers["Authorization"] = `Bearer ${newToken}`;
      resp = await fetch(`${API_URL}${path}`, { ...options, headers });
    } catch {
      clearTokens();
      throw new Error("Unauthorized");
    }
  }

  if (!resp.ok) {
    let detail = "Request failed";
    try {
      const body = await resp.json();
      detail = body.detail || detail;
      if (Array.isArray(detail)) {
        detail = detail.map((e: { msg: string }) => e.msg).join(", ");
      }
    } catch {
      // ignore parse error
    }
    const err = new Error(detail) as Error & { status: number };
    err.status = resp.status;
    throw err;
  }

  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

// ---------- Auth ----------
export const authApi = {
  register: (data: { name: string; email: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request<TokenPair>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => request<User>("/auth/me"),
};

// ---------- Groups ----------
export const groupsApi = {
  list: () => request<Group[]>("/groups"),
  create: (data: { name: string; currency?: string }) =>
    request<GroupDetail>("/groups", { method: "POST", body: JSON.stringify(data) }),
  get: (id: number) => request<GroupDetail>(`/groups/${id}`),
  addMember: (id: number, email: string) =>
    request<GroupDetail>(`/groups/${id}/members`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  removeMember: (groupId: number, userId: number) =>
    request<void>(`/groups/${groupId}/members/${userId}`, { method: "DELETE" }),
  balances: (id: number) => request<GroupBalances>(`/groups/${id}/balances`),
};

// ---------- Expenses ----------
export const expensesApi = {
  list: (groupId: number) =>
    request<Expense[]>(`/groups/${groupId}/expenses`),
  create: (
    groupId: number,
    data: {
      description: string;
      total_amount: string;
      split_type: string;
      participants: { user_id: number; paid_share: string; owed_share: string }[];
    },
  ) =>
    request<Expense>(`/groups/${groupId}/expenses`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  delete: (groupId: number, expenseId: number) =>
    request<void>(`/groups/${groupId}/expenses/${expenseId}`, { method: "DELETE" }),
};

// ---------- Settlements ----------
export const settlementsApi = {
  list: (groupId: number) =>
    request<Settlement[]>(`/groups/${groupId}/settlements`),
  create: (
    groupId: number,
    data: { from_user_id: number; to_user_id: number; amount: string },
  ) =>
    request<Settlement>(`/groups/${groupId}/settlements`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
