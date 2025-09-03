import { api } from './index';

export interface BillingFeatureFlags {
  billingEnabled: boolean;
  paywallMode: string;
  testMode?: boolean;
}

export interface SubscriptionInfo {
  plan: string;
  status: string;
  provider: string;
  startDate: string;
  endDate: string | null;
}

export interface BillingStatus {
  featureFlags: BillingFeatureFlags;
  subscription: SubscriptionInfo | null;
}

export const getBillingStatus = () =>
  api.get<BillingStatus>('/billing/status');

export const startTrial = () =>
  api.post<SubscriptionInfo>('/billing/trial', {});

export const subscribePlan = (plan: string) =>
  api.post<{ id: string; url: string }>(`/billing/subscribe?plan=${plan}`, {});
