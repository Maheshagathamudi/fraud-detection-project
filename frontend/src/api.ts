export type Action = "approve" | "review" | "decline";
export interface Reason { rule_id: string; points: number; reason: string }
export interface Transaction { id: number; amount: string; currency: string; occurred_at: string; score: number; action: Action; review_status: "not_required" | "pending" | "approved" | "declined"; model_probability: number | null; model_version: string | null; policy_version: string; reasons: Reason[]; created_at: string }
export interface Summary { total: number; actions: Record<Action, number>; open_reviews: number; average_score: number }

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

const api = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) { const body = await response.json(); throw new Error(body.detail ?? `Request failed (${response.status})`); }
  return response.json() as Promise<T>;
};
export const getTransactions = () => api<{ items: Transaction[]; total: number }>("/transactions?limit=100");
export const getReviewQueue = () => api<{ items: Transaction[]; total: number }>("/transactions/review-queue?limit=100");
export const getSummary = () => api<Summary>("/transactions/summary");
export const resolveReview = (id: number, outcome: "approve" | "decline") => api<Transaction>(`/transactions/${id}/review`, { method: "POST", body: JSON.stringify({ outcome }) });
export const sendSample = (kind: "normal" | "high-risk") => {
  const id = crypto.randomUUID();
  const payload = { amount: kind === "high-risk" ? "3900.00" : (20 + Math.random() * 480).toFixed(2), currency: "USD", customer_token: kind === "high-risk" ? "demo-fast-customer" : `demo-customer-${Math.floor(Math.random() * 40)}`, instrument_token: kind === "high-risk" ? "demo-fast-instrument" : `demo-instrument-${Math.floor(Math.random() * 60)}`, merchant_token: `demo-merchant-${Math.floor(Math.random() * 8)}`, occurred_at: new Date().toISOString() };
  return api<Transaction>("/transactions", { method: "POST", headers: { "Idempotency-Key": id }, body: JSON.stringify(payload) });
};
