import { api } from '@/api';
import { HttpError } from '@/lib/http';
import { toast } from '@/components/ui/use-toast';
import type {
  Profile,
  PatchProfileDto,
  RapidInsulin,
  TherapyType,
} from './types';

export async function getProfile(): Promise<Profile | null> {
  try {
    return await api.get<Profile>('/profile');
  } catch (error) {
    if (error instanceof HttpError) {
      if (error.status === 404 || error.status === 422) {
        toast({
          title: 'User not registered—please complete onboarding.',
          description: 'Redirecting to onboarding...',
        });
        if (typeof window !== 'undefined') {
          try {
            window.location.href = '/profile?flow=onboarding';
          } catch {
            /* ignore navigation errors in non-browser environments */
          }
        }
        return null;
      }
      console.error('Failed to load profile:', error);
      throw new Error(`Не удалось получить профиль: ${error.message}`);
    }
    console.error('Failed to load profile:', error);
    const message =
      error instanceof Error ? error.message : 'Unknown error';
    throw new Error(`Не удалось получить профиль: ${message}`);
  }
}

export async function saveProfile({
  telegramId,
  icr,
  cf,
  target,
  low,
  high,
  quietStart,
  quietEnd,
  timezone,
  timezoneAuto,
  sosContact,
  sosAlertsEnabled,
  therapyType,
}: {
  telegramId: number;
  target: number;
  low: number;
  high: number;
  icr?: number;
  cf?: number;
  quietStart?: string;
  quietEnd?: string;
  timezone?: string;
  timezoneAuto?: boolean;
  sosContact?: string | null;
  sosAlertsEnabled?: boolean;
  therapyType?: TherapyType | null;
}): Promise<unknown> {
  try {
    const body: Record<string, unknown> = {
      telegramId,
      target,
      low,
      high,
    };

    if (icr !== undefined) {
      body.icr = icr;
    }

    if (cf !== undefined) {
      body.cf = cf;
    }

    if (quietStart !== undefined) {
      body.quietStart = quietStart;
    }

    if (quietEnd !== undefined) {
      body.quietEnd = quietEnd;
    }

    if (timezone !== undefined) {
      body.timezone = timezone;
    }

    if (timezoneAuto !== undefined) {
      body.timezoneAuto = timezoneAuto;
    }

    if (sosContact !== undefined) {
      body.sosContact = sosContact;
    }

    if (sosAlertsEnabled !== undefined) {
      body.sosAlertsEnabled = sosAlertsEnabled;
    }

    if (therapyType !== undefined) {
      body.therapyType = therapyType;
    }

    return await api.post('/profile', body);
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось сохранить профиль: ${error.message}`);
    }
    throw error;
  }
}

export async function patchProfile(payload: PatchProfileDto) {
  try {
    const { sosContact, sosAlertsEnabled, ...rest } = payload;
    const body = Object.fromEntries(
      Object.entries(rest).filter(([, value]) => value !== undefined),
    ) as Record<string, unknown>;

    if (sosContact !== undefined) {
      body.sosContact = sosContact;
    }

    if (sosAlertsEnabled !== undefined) {
      body.sosAlertsEnabled = sosAlertsEnabled;
    }

    return await api.patch<unknown>('/profile', body);
  } catch (error) {
    console.error('Failed to update profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось обновить профиль: ${error.message}`);
    }
    throw error;
  }
}

export type { RapidInsulin, PatchProfileDto, Profile };
