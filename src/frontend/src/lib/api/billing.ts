// ─── Billing API ───────────────────────────────────────────
// Backend routes: /api/v1/billing/...

import { apiClient } from '@/lib/api';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ─── Types ─────────────────────────────────────────────────

export interface SubscriptionPlan {
  id: string;
  name: string;
  slug: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  currency: string;
  features: string[];
  is_active: boolean;
  created_at: string;
}

export interface Subscription {
  id: string;
  tenant_id: string;
  plan_id: string;
  plan: SubscriptionPlan;
  status: 'active' | 'trialing' | 'past_due' | 'canceled' | 'incomplete';
  current_period_start: string;
  current_period_end: string;
  trial_end?: string;
  cancel_at_period_end: boolean;
  billing_anchor: string;
  created_at: string;
  updated_at: string;
}

export interface Invoice {
  id: string;
  tenant_id: string;
  subscription_id: string;
  number: string;
  amount_due: number;
  amount_paid: number;
  amount_remaining: number;
  currency: string;
  status: 'draft' | 'open' | 'paid' | 'void' | 'uncollectible';
  billing_reason: string;
  due_date: string;
  paid_at?: string;
  lines: InvoiceLineItem[];
  created_at: string;
}

export interface InvoiceLineItem {
  id: string;
  invoice_id: string;
  description: string;
  amount: number;
  currency: string;
  period_start: string;
  period_end: string;
  quantity: number;
  unit_price: number;
}

export interface Wallet {
  id: string;
  tenant_id: string;
  balance: number;
  currency: string;
  credit_limit: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WalletTransaction {
  id: string;
  wallet_id: string;
  type: 'credit' | 'debit' | 'refund' | 'adjustment';
  amount: number;
  currency: string;
  balance_after: number;
  description: string;
  reference_type?: string;
  reference_id?: string;
  created_at: string;
}

export interface UsageRecord {
  id: string;
  tenant_id: string;
  metric_name: string;
  quantity: number;
  unit: string;
  recorded_at: string;
}

export interface UsageSummary {
  metric_name: string;
  unit: string;
  total_quantity: number;
  period_start: string;
  period_end: string;
}

export interface UsageRecordRequest {
  metric_name: string;
  quantity: number;
  unit: string;
  recorded_at?: string;
}

export interface ChangePlanRequest {
  plan_id: string;
  billing_anchor?: 'current_period' | 'next_period';
}

export interface PaymentMethod {
  id: string;
  tenant_id: string;
  type: 'card' | 'bank_transfer' | 'wallet';
  is_default: boolean;
  last_four?: string;
  expiry_month?: number;
  expiry_year?: number;
  brand?: string;
  created_at: string;
}

// ─── Billing API Client ────────────────────────────────────

export const billingApi = {
  // ── Subscriptions ──

  /** List available subscription plans */
  listPlans: () =>
    apiClient.get<SubscriptionPlan[]>('/api/v1/billing/plans').then(
      (items) => ({ data: items }) as unknown as ApiResponse<SubscriptionPlan[]>
    ),

  /** Get current subscription */
  getSubscription: () =>
    apiClient.get<Subscription>('/api/v1/billing/subscriptions/current').then(
      (data) => ({ data }) as ApiResponse<Subscription>
    ),

  /** Change subscription plan */
  changePlan: (data: ChangePlanRequest) =>
    apiClient.post<Subscription>('/api/v1/billing/subscriptions/change', data).then(
      (data) => ({ data }) as ApiResponse<Subscription>
    ),

  /** Cancel subscription at period end */
  cancelSubscription: () =>
    apiClient.post<void>('/api/v1/billing/subscriptions/cancel'),

  /** Reactivate canceled subscription */
  reactivateSubscription: () =>
    apiClient.post<void>('/api/v1/billing/subscriptions/reactivate'),

  // ── Invoices ──

  /** List invoices */
  listInvoices: (params?: { page?: number; limit?: number; status?: string }) =>
    apiClient
      .get<{ items: Invoice[]; total: number; page: number; page_size: number }>(
        '/api/v1/billing/invoices',
        params as Record<string, string | number | boolean | undefined>
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<Invoice>>,

  /** Get invoice by ID */
  getInvoice: (id: string) =>
    apiClient.get<Invoice>(`/api/v1/billing/invoices/${id}`).then(
      (data) => ({ data }) as ApiResponse<Invoice>
    ),

  /** Download invoice PDF */
  downloadInvoice: (id: string) =>
    apiClient.get<Blob>(`/api/v1/billing/invoices/${id}/pdf`),

  // ── Wallet ──

  /** Get wallet balance */
  getWallet: () =>
    apiClient.get<Wallet>('/api/v1/billing/wallet').then(
      (data) => ({ data }) as ApiResponse<Wallet>
    ),

  /** List wallet transactions */
  listWalletTransactions: (params?: { page?: number; limit?: number }) =>
    apiClient
      .get<{ items: WalletTransaction[]; total: number; page: number; page_size: number }>(
        '/api/v1/billing/wallet/transactions',
        params as Record<string, string | number | boolean | undefined>
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<WalletTransaction>>,

  /** Add credit to wallet */
  addWalletCredit: (amount: number, currency?: string) =>
    apiClient.post<WalletTransaction>('/api/v1/billing/wallet/credit', {
      amount,
      currency: currency ?? 'USD',
    }).then((data) => ({ data }) as ApiResponse<WalletTransaction>),

  // ── Usage ──

  /** Report usage */
  reportUsage: (records: UsageRecordRequest[]) =>
    apiClient.post<void>('/api/v1/billing/usage', { records }),

  /** Get usage summary for current period */
  getUsageSummary: () =>
    apiClient.get<UsageSummary[]>('/api/v1/billing/usage/summary').then(
      (items) => ({ data: items }) as unknown as ApiResponse<UsageSummary[]>
    ),

  // ── Payment Methods ──

  /** List payment methods */
  listPaymentMethods: () =>
    apiClient.get<PaymentMethod[]>('/api/v1/billing/payment-methods').then(
      (items) => ({ data: items }) as unknown as ApiResponse<PaymentMethod[]>
    ),

  /** Set default payment method */
  setDefaultPaymentMethod: (id: string) =>
    apiClient.patch<void>(`/api/v1/billing/payment-methods/${id}/default`),

  /** Remove payment method */
  removePaymentMethod: (id: string) =>
    apiClient.delete<void>(`/api/v1/billing/payment-methods/${id}`),
};
