import React from 'react';
import { render, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const toast = vi.fn();
let searchParams = new URLSearchParams();

vi.mock('../src/features/profile/api', () => ({
  saveProfile: vi.fn(),
  getProfile: vi.fn(),
  patchProfile: vi.fn(),
}));

vi.mock('../src/hooks/use-toast', () => ({
  useToast: () => ({ toast }),
}));

vi.mock('../src/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: null }),
}));

vi.mock('../src/hooks/useTelegramInitData', () => ({
  useTelegramInitData: vi.fn(),
}));

vi.mock('@/shared/api/onboarding', () => ({
  postOnboardingEvent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [searchParams, vi.fn()],
}));

vi.mock('../src/pages/resolveTelegramId', () => ({
  resolveTelegramId: vi.fn(),
}));

import Profile from '../src/pages/Profile';
import { saveProfile, getProfile, patchProfile } from '../src/features/profile/api';
import { resolveTelegramId } from '../src/pages/resolveTelegramId';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';
import { useTranslation } from '../src/i18n';
import type { RapidInsulin } from '../src/features/profile/types';

const originalSupportedValuesOf = (Intl as any).supportedValuesOf;
describe('Profile page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getProfile as vi.Mock).mockResolvedValue({
      telegramId: 0,
      icr: 12,
      cf: 2.5,
      target: 6,
      low: 4,
      high: 10,
      dia: 4,
      preBolus: 15,
      roundStep: 0.5,
      carbUnits: 'g',
      gramsPerXe: 12,
      rapidInsulinType: 'aspart' as RapidInsulin,
      maxBolus: 10,
      afterMealMinutes: 120,
      timezone: 'Europe/Moscow',
      timezoneAuto: false,
      therapyType: 'insulin',
    });
    const realDTF = Intl.DateTimeFormat;
    const realResolved = realDTF.prototype.resolvedOptions;
    vi.spyOn(Intl, 'DateTimeFormat').mockImplementation((...args: any[]) => {
      const formatter = new realDTF(...(args as []));
      return Object.assign(formatter, {
        resolvedOptions: () => ({
          ...realResolved.call(formatter),
          timeZone: 'Europe/Berlin',
        }),
      });
    });
    (Intl as any).supportedValuesOf = vi
      .fn()
      .mockReturnValue(['Europe/Moscow', 'Europe/Berlin']);
  });

  afterEach(() => {
    cleanup();
    (Intl as any).supportedValuesOf = originalSupportedValuesOf;
    vi.restoreAllMocks();
    searchParams = new URLSearchParams();
  });

  it('displays carbUnits options using localized text', () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    const { getByLabelText } = render(<Profile />);
    const { t } = useTranslation();
    const select = getByLabelText(
      t('profileHelp.carbUnits.title'),
    ) as HTMLSelectElement;
    expect(select.options[0].text).toBe(
      t('profileHelp.carbUnits.options.g'),
    );
    expect(select.options[1].text).toBe(
      t('profileHelp.carbUnits.options.xe'),
    );
  });

  it('blocks save without telegramId and shows toast', () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(undefined);
    const { getByText } = render(<Profile />);
    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(patchProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description: 'Некорректный ID пользователя',
        variant: 'destructive',
      }),
    );
  });

  it('blocks save with non-numeric id in initData and shows toast', async () => {
    const { resolveTelegramId: actualResolveTelegramId } = await vi.importActual<
      typeof import('../src/pages/resolveTelegramId')
    >('../src/pages/resolveTelegramId');
    (resolveTelegramId as vi.Mock).mockImplementation(
      actualResolveTelegramId,
    );
    (useTelegramInitData as vi.Mock).mockReturnValue(
      'user=%7B%22id%22%3A%22notnumber%22%7D',
    );
    const { getByText } = render(<Profile />);
    fireEvent.click(getByText('Сохранить настройки'));
    expect(resolveTelegramId).toHaveBeenCalledWith(
      null,
      expect.stringContaining('notnumber'),
    );
    expect(saveProfile).not.toHaveBeenCalled();
    expect(patchProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description: 'Некорректный ID пользователя',
        variant: 'destructive',
      }),
    );
  });

  it('renders localized rapid insulin type options', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    const { getByLabelText } = render(<Profile />);

    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });

    const options = Array.from(
      (
        getByLabelText('Тип быстрого инсулина', {
          selector: 'select',
        }) as HTMLSelectElement
      ).options,
    ).map((o) => o.text);

    expect(options).toEqual(['Аспарт', 'Лиспро', 'Глулизин', 'Регуляр']);
  });

  it('blocks save with invalid numeric input and shows toast', () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);

    const { getByText, getByPlaceholderText } = render(<Profile />);
    const icrInput = getByPlaceholderText('12');
    fireEvent.change(icrInput, { target: { value: '0' } });

    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(patchProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description:
          'Проверьте, что все значения положительны, нижний порог меньше' +
          ' верхнего, а целевой уровень между ними',
        variant: 'destructive',
      }),
    );
  });

  it('toggles grams per XE input with carb unit', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    const { queryByLabelText, getByDisplayValue } = render(<Profile />);

    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });

    expect(queryByLabelText('Граммов на 1 ХЕ')).toBeNull();
    const select = getByDisplayValue('г') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: 'xe' } });
    expect(queryByLabelText('Граммов на 1 ХЕ')).not.toBeNull();
  });

  it('blocks save when target is out of range and shows toast', () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);

    const { getByText, getByPlaceholderText } = render(<Profile />);
    const targetInput = getByPlaceholderText('6.0');
    fireEvent.change(targetInput, { target: { value: '12' } });

    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(patchProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description:
          'Проверьте, что все значения положительны, нижний порог меньше' +
          ' верхнего, а целевой уровень между ними',
        variant: 'destructive',
      }),
    );
  });

  it('saves profile when values with commas are provided', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (saveProfile as vi.Mock).mockResolvedValue(undefined);

    const { getByText, getByPlaceholderText } = render(<Profile />);

    await waitFor(() => {
      expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('12');
    });

    const icrInput = getByPlaceholderText('12') as HTMLInputElement;
    fireEvent.change(icrInput, { target: { value: '1,5' } });
    expect(icrInput.value).toBe('1,5');

    const cfInput = getByPlaceholderText('2.5') as HTMLInputElement;
    fireEvent.change(cfInput, { target: { value: '2,5' } });
    expect(cfInput.value).toBe('2,5');

    const targetInput = getByPlaceholderText('6.0') as HTMLInputElement;
    fireEvent.change(targetInput, { target: { value: '5,5' } });
    expect(targetInput.value).toBe('5,5');

    const lowInput = getByPlaceholderText('4.0') as HTMLInputElement;
    fireEvent.change(lowInput, { target: { value: '4,0' } });
    expect(lowInput.value).toBe('4,0');

    const highInput = getByPlaceholderText('10.0') as HTMLInputElement;
    fireEvent.change(highInput, { target: { value: '10,0' } });
    expect(highInput.value).toBe('10,0');

    fireEvent.click(getByText('Сохранить настройки'));

    await waitFor(() => {
      expect(saveProfile).toHaveBeenCalledWith({
        telegramId: 123,
        icr: 1.5,
        cf: 2.5,
        target: 5.5,
        low: 4,
        high: 10,
      });
      expect(patchProfile).not.toHaveBeenCalled();
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Профиль сохранен' }),
      );
    });
  });

  const nonInsulinTherapies: Array<'none' | 'tablets'> = ['none', 'tablets'];

  it.each(nonInsulinTherapies)(
    'hides insulin fields for %s therapy',
    async (therapy) => {
      (resolveTelegramId as vi.Mock).mockReturnValue(123);
      (getProfile as vi.Mock).mockResolvedValueOnce({
        telegramId: 123,
        icr: 12,
        cf: 2.5,
        target: 6,
        low: 4,
        high: 10,
        dia: 4,
        preBolus: 15,
        roundStep: 0.5,
        carbUnits: 'g',
        gramsPerXe: 12,
        rapidInsulinType: 'aspart' as RapidInsulin,
        maxBolus: 10,
        afterMealMinutes: 120,
        timezone: 'Europe/Moscow',
        timezoneAuto: false,
        therapyType: therapy,
      });
      const { queryByLabelText } = render(<Profile therapyType={therapy} />);
      await waitFor(() => {
        expect(getProfile).toHaveBeenCalled();
      });
      expect(queryByLabelText(/ICR/)).toBeNull();
      expect(queryByLabelText(/Коэффициент коррекции/)).toBeNull();
      expect(queryByLabelText(/DIA/)).toBeNull();
      expect(queryByLabelText(/Пре-болюс/)).toBeNull();
      expect(queryByLabelText(/Тип быстрого инсулина/)).toBeNull();
      expect(queryByLabelText(/Максимальный болюс/)).toBeNull();
    },
  );

  it.each(nonInsulinTherapies)(
    'does not show toast when insulin fields missing for %s therapy',
    async (therapy) => {
      (resolveTelegramId as vi.Mock).mockReturnValue(123);
      (getProfile as vi.Mock).mockResolvedValueOnce({
        telegramId: 123,
        target: 6,
        low: 4,
        high: 10,
        roundStep: 1,
        carbUnits: 'g',
        gramsPerXe: 12,
        afterMealMinutes: 120,
        timezone: 'Europe/Moscow',
        timezoneAuto: false,
        therapyType: therapy,
      });
      render(<Profile therapyType={therapy} />);
      await waitFor(() => {
        expect(getProfile).toHaveBeenCalled();
      });
      expect(toast).not.toHaveBeenCalled();
    },
  );

  it.each(nonInsulinTherapies)(
    'shows toast when non-insulin fields missing for %s therapy',
    async (therapy) => {
      (resolveTelegramId as vi.Mock).mockReturnValue(123);
      (getProfile as vi.Mock).mockResolvedValueOnce({
        telegramId: 123,
        low: 4,
        high: 10,
        roundStep: 1,
        carbUnits: 'g',
        gramsPerXe: 12,
        afterMealMinutes: 120,
        timezone: 'Europe/Moscow',
        timezoneAuto: false,
        therapyType: therapy,
      });
      render(<Profile therapyType={therapy} />);
      await waitFor(() => {
        expect(getProfile).toHaveBeenCalled();
      });
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Ошибка',
          description: 'Профиль заполнен не полностью',
          variant: 'destructive',
        }),
      );
    },
  );

  it('allows zero pre-bolus and after-meal delay for insulin therapy', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (getProfile as vi.Mock).mockResolvedValueOnce({
      telegramId: 123,
      icr: 12,
      cf: 2.5,
      target: 6,
      low: 4,
      high: 10,
      dia: 4,
      preBolus: 0,
      roundStep: 0.5,
      carbUnits: 'g',
      gramsPerXe: 12,
      rapidInsulinType: 'aspart' as RapidInsulin,
      maxBolus: 10,
      afterMealMinutes: 0,
      timezone: 'Europe/Moscow',
      timezoneAuto: false,
      therapyType: 'insulin',
    });

    render(<Profile />);
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalled();
    });
    expect(toast).not.toHaveBeenCalled();
  });

  it.each(nonInsulinTherapies)(
    'allows zero after-meal delay for %s therapy',
    async (therapy) => {
      (resolveTelegramId as vi.Mock).mockReturnValue(123);
      (getProfile as vi.Mock).mockResolvedValueOnce({
        telegramId: 123,
        target: 6,
        low: 4,
        high: 10,
        roundStep: 1,
        carbUnits: 'g',
        gramsPerXe: 12,
        afterMealMinutes: 0,
        timezone: 'Europe/Moscow',
        timezoneAuto: false,
        therapyType: therapy,
      });
      render(<Profile therapyType={therapy} />);
      await waitFor(() => {
        expect(getProfile).toHaveBeenCalled();
      });
      expect(toast).not.toHaveBeenCalled();
    },
  );

  it('renders advanced bolus fields', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    const { getByPlaceholderText } = render(<Profile />);
    await waitFor(() => {
      expect(getByPlaceholderText('15')).toBeTruthy();
      expect(getByPlaceholderText('0.5')).toBeTruthy();
      expect(getByPlaceholderText('120')).toBeTruthy();
    });
  });

  it('validates advanced bolus fields', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    const { getByText, getByPlaceholderText } = render(<Profile />);
    await waitFor(() => {
      expect((getByPlaceholderText('15') as HTMLInputElement).value).toBe('15');
    });
    const preInput = getByPlaceholderText('15');
    fireEvent.change(preInput, { target: { value: '-1' } });
    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(patchProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Ошибка' }),
    );
  });

  it('submits advanced bolus fields and sends patch only for changes', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (saveProfile as vi.Mock).mockResolvedValue(undefined);
    const { getByText, getByPlaceholderText, getByDisplayValue, getByLabelText } =
      render(<Profile />);
    await waitFor(() => {
      expect((getByPlaceholderText('4') as HTMLInputElement).value).toBe('4');
    });
    fireEvent.change(getByPlaceholderText('4'), { target: { value: '5' } });
    fireEvent.change(getByPlaceholderText('15'), { target: { value: '20' } });
    fireEvent.change(getByPlaceholderText('0.5'), { target: { value: '1' } });
    const carbSelect = getByDisplayValue('г') as HTMLSelectElement;
    fireEvent.change(carbSelect, { target: { value: 'xe' } });
    fireEvent.change(getByLabelText('Граммов на 1 ХЕ'), {
      target: { value: '15' },
    });
    fireEvent.change(getByPlaceholderText('10'), { target: { value: '12' } });
    fireEvent.change(getByPlaceholderText('120'), { target: { value: '90' } });
    fireEvent.change(getByDisplayValue('aspart'), {
      target: { value: 'lispro' },
    });

    fireEvent.click(getByText('Сохранить настройки'));

    await waitFor(() => {
      expect(patchProfile).toHaveBeenCalledWith({
        dia: 5,
        preBolus: 20,
        roundStep: 1,
        carbUnits: 'xe',
        gramsPerXe: 15,
        rapidInsulinType: 'lispro' as RapidInsulin,
        maxBolus: 12,
        afterMealMinutes: 90,
      });
      expect(saveProfile).toHaveBeenCalled();
    });
  });

  it('auto updates timezone on mount when timezoneAuto is true', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (getProfile as vi.Mock).mockResolvedValue({
      telegramId: 123,
      icr: 12,
      cf: 2.5,
      target: 6,
      low: 4,
      high: 10,
      dia: 4,
      preBolus: 15,
      roundStep: 0.5,
      carbUnits: 'g',
      gramsPerXe: 12,
      rapidInsulinType: 'aspart' as RapidInsulin,
      maxBolus: 10,
      afterMealMinutes: 120,
      timezone: 'Europe/Moscow',
      timezoneAuto: true,
      therapyType: 'insulin',
    });

    render(<Profile />);

    await waitFor(() => {
      expect(patchProfile).toHaveBeenCalledWith({
        timezone: 'Europe/Berlin',
        timezoneAuto: true,
      });
    });
  });

  it('allows manual timezone selection and sends to server on save', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (saveProfile as vi.Mock).mockResolvedValue(undefined);
    (getProfile as vi.Mock).mockResolvedValue({
      telegramId: 123,
      icr: 6,
      cf: 3,
      target: 6,
      low: 4,
      high: 10,
      dia: 4,
      preBolus: 15,
      roundStep: 0.5,
      carbUnits: 'g',
      gramsPerXe: 12,
      rapidInsulinType: 'aspart' as RapidInsulin,
      maxBolus: 10,
      afterMealMinutes: 120,
      timezone: 'Europe/Moscow',
      timezoneAuto: false,
      therapyType: 'insulin',
    });

    const { getByLabelText, getByText, getByPlaceholderText } = render(<Profile />);

    await waitFor(() => {
      expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('6');
    });

    const tzInput = getByLabelText('Часовой пояс') as HTMLInputElement;
    fireEvent.change(tzInput, { target: { value: 'Europe/Berlin' } });

    fireEvent.click(getByText('Сохранить настройки'));

    await waitFor(() => {
      expect(patchProfile).toHaveBeenCalledWith({
        timezone: 'Europe/Berlin',
        timezoneAuto: false,
      });
      expect(saveProfile).toHaveBeenCalled();
    });
  });

  it('sends therapyType change to server on save', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (saveProfile as vi.Mock).mockResolvedValue(undefined);
    const { getByLabelText, getByText } = render(<Profile />);
    const { t } = useTranslation();

    await waitFor(() => {
      expect(
        (getByLabelText(
          t('profileHelp.therapyType.title'),
        ) as HTMLSelectElement).value,
      ).toBe('insulin');
    });

    const select = getByLabelText(
      t('profileHelp.therapyType.title'),
    ) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: 'tablets' } });

    fireEvent.click(getByText('Сохранить настройки'));

    await waitFor(() => {
      expect(patchProfile).toHaveBeenCalledWith({ therapyType: 'tablets' });
    });
  });

  it('loads profile on mount and updates form', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (getProfile as vi.Mock).mockResolvedValue({
      telegramId: 123,
      icr: 15,
      cf: 3,
      target: 5,
      low: 3,
      high: 8,
      dia: 4,
      preBolus: 15,
      roundStep: 0.5,
      carbUnits: 'g',
      gramsPerXe: 12,
      rapidInsulinType: 'aspart' as RapidInsulin,
      maxBolus: 10,
      afterMealMinutes: 120,
      therapyType: 'insulin',
    });

    const { getByPlaceholderText } = render(<Profile />);
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });
    expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('15');
    expect((getByPlaceholderText('2.5') as HTMLInputElement).value).toBe('3');
  });

  it('defaults when profile data is incomplete without toast', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (getProfile as vi.Mock).mockResolvedValue({
      telegramId: 123,
      icr: 15,
      cf: 3,
      dia: 4,
      preBolus: 15,
      roundStep: 0.5,
      carbUnits: 'g',
      gramsPerXe: 12,
      rapidInsulinType: 'aspart' as RapidInsulin,
      maxBolus: 10,
      afterMealMinutes: 120,
      therapyType: 'insulin',
    });

    const { getByPlaceholderText } = render(<Profile />);
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });
    expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('15');
    expect((getByPlaceholderText('2.5') as HTMLInputElement).value).toBe('3');
    expect((getByPlaceholderText('6.0') as HTMLInputElement).value).toBe('');
    expect((getByPlaceholderText('4.0') as HTMLInputElement).value).toBe('');
    expect(toast).not.toHaveBeenCalled();
    expect(patchProfile).not.toHaveBeenCalled();
  });

  it('shows toast and clears zero values from profile data', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (getProfile as vi.Mock).mockResolvedValue({
      telegramId: 123,
      icr: 15,
      cf: 0,
      target: 5,
      low: 3,
      high: 8,
      dia: 4,
      preBolus: 15,
      roundStep: 0.5,
      carbUnits: 'g',
      gramsPerXe: 12,
      rapidInsulinType: 'aspart' as RapidInsulin,
      maxBolus: 10,
      afterMealMinutes: 120,
      therapyType: 'insulin',
    });

    const { getByPlaceholderText } = render(<Profile />);
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });

    expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('15');
    expect((getByPlaceholderText('2.5') as HTMLInputElement).value).toBe('');
    expect((getByPlaceholderText('6.0') as HTMLInputElement).value).toBe('5');
    expect((getByPlaceholderText('4.0') as HTMLInputElement).value).toBe('3');
    expect((getByPlaceholderText('10.0') as HTMLInputElement).value).toBe('8');

    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description: 'Профиль заполнен не полностью',
        variant: 'destructive',
      }),
    );
    expect(patchProfile).not.toHaveBeenCalled();
  });

  it.each([
    ['insulin', 'g', false],
    ['insulin', 'xe', true],
    ['tablets', 'g', false],
    ['tablets', 'xe', true],
  ])(
    'handles gramsPerXe requirement for therapyType %s and carbUnits %s',
    async (
      therapyType: 'insulin' | 'tablets',
      unit: 'g' | 'xe',
      shouldToast: boolean,
    ) => {
      (resolveTelegramId as vi.Mock).mockReturnValue(123);
      (getProfile as vi.Mock).mockResolvedValue({
        telegramId: 123,
        icr: 15,
        cf: 3,
        target: 6,
        low: 4,
        high: 10,
        dia: 4,
        preBolus: 15,
        roundStep: 0.5,
        carbUnits: unit,
        gramsPerXe: 0,
        rapidInsulinType: 'aspart' as RapidInsulin,
        maxBolus: 10,
        afterMealMinutes: 120,
        timezone: 'Europe/Moscow',
        timezoneAuto: false,
        therapyType,
      });

      render(<Profile />);
      await waitFor(() => {
        expect(getProfile).toHaveBeenCalledWith(123);
      });

      if (shouldToast) {
        expect(toast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Ошибка',
            description: 'Профиль заполнен не полностью',
            variant: 'destructive',
          }),
        );
      } else {
        expect(toast).not.toHaveBeenCalled();
      }
    },
  );

  it('shows toast when profile load fails', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (getProfile as vi.Mock).mockRejectedValue(new Error('load failed'));

    const { getByPlaceholderText } = render(<Profile />);
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description: 'load failed',
        variant: 'destructive',
      }),
    );
    expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('');
    expect(patchProfile).not.toHaveBeenCalled();
  });

  it('shows toast when profile is missing', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (getProfile as vi.Mock).mockResolvedValue(null);

    render(<Profile />);
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });
    const { t } = useTranslation();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: t('profile.error'),
        description: t('profile.notFound'),
        variant: 'destructive',
      }),
    );
  });

  it('shows warning modal and blocks save until confirmation', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    const { getByText, getByPlaceholderText } = render(<Profile />);

    await waitFor(() => {
      expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('12');
    });

    fireEvent.click(getByText('Сохранить настройки'));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Проверьте значения' }),
      );
    });

    expect(
      getByText(
        'ICR больше 8 и CF меньше 3. Пожалуйста, убедитесь в корректности введенных данных',
      ),
    ).toBeTruthy();
    expect(saveProfile).not.toHaveBeenCalled();
    expect(patchProfile).not.toHaveBeenCalled();
  });

  it('saves after user confirms warning', async () => {
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (saveProfile as vi.Mock).mockResolvedValue(undefined);

    const { getByText, getByPlaceholderText } = render(<Profile />);

    await waitFor(() => {
      expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('12');
    });

    fireEvent.click(getByText('Сохранить настройки'));

    await waitFor(() => getByText('Продолжить'));
    fireEvent.click(getByText('Продолжить'));

    await waitFor(() => {
      expect(saveProfile).toHaveBeenCalledWith({
        telegramId: 123,
        icr: 12,
        cf: 2.5,
        target: 6,
        low: 4,
        high: 10,
      });
      expect(patchProfile).not.toHaveBeenCalled();
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Профиль сохранен' }),
      );
    });
  });

});

describe('resolveTelegramId', () => {
  it('returns undefined for NaN user id', async () => {
    const { resolveTelegramId } = await vi.importActual<
      typeof import('../src/pages/resolveTelegramId')
    >('../src/pages/resolveTelegramId');
    expect(resolveTelegramId({ id: Number.NaN }, null)).toBeUndefined();
  });

  it('returns undefined for non-numeric id in initData', async () => {
    const { resolveTelegramId } = await vi.importActual<
      typeof import('../src/pages/resolveTelegramId')
    >('../src/pages/resolveTelegramId');
    const initData = `user=${encodeURIComponent(
      JSON.stringify({ id: 'abc' }),
    )}`;
    expect(resolveTelegramId(null, initData)).toBeUndefined();
  });

  it('treats 0 as valid user id and ignores initData', async () => {
    const { resolveTelegramId } = await vi.importActual<
      typeof import('../src/pages/resolveTelegramId')
    >('../src/pages/resolveTelegramId');
    const initData = `user=${encodeURIComponent(
      JSON.stringify({ id: 123 }),
    )}`;
    expect(resolveTelegramId({ id: 0 }, initData)).toBe(0);
  });
});
