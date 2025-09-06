import { api } from './index';

export interface BillingFeatureFlags {
  billingEnabled: boolean;
  paywallMode: string;
  testMode: boolean;
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

export const getBillingStatus = (userId: string) => {
  const params = new URLSearchParams({ user_id: userId });
  return api.get<BillingStatus>(`/billing/status?${params.toString()}`);
};

export const startTrial = (userId: string) =>
  api.post<SubscriptionInfo>(`/billing/trial?user_id=${userId}`, {});

export const subscribePlan = (userId: string, plan: string) =>
  api.post<{ id: string; url: string }>(
    `/billing/subscribe?user_id=${userId}&plan=${plan}`,
    {},
  );
