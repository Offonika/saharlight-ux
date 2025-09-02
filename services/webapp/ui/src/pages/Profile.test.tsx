import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import Profile from './Profile';
import React from 'react';
import { describe, it, vi, expect } from 'vitest';

// mock dependencies that Profile relies on
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast: vi.fn() }) }));
vi.mock('@/i18n', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock('@/hooks/useTelegram', () => ({ useTelegram: () => ({ user: undefined }) }));
vi.mock('@/hooks/useTelegramInitData', () => ({ useTelegramInitData: () => undefined }));
vi.mock('./resolveTelegramId', () => ({ resolveTelegramId: () => undefined }));
vi.mock('@/features/profile/api', () => ({
  saveProfile: vi.fn(),
  getProfile: vi.fn(),
  patchProfile: vi.fn(),
}));
vi.mock('@/api/timezones', () => ({ getTimezones: vi.fn() }));
vi.mock('lucide-react', () => ({ Save: () => <svg /> }));
vi.mock('@/components/MedicalHeader', () => ({ MedicalHeader: ({ children }: any) => <div>{children}</div> }));
vi.mock('@/components/MedicalButton', () => ({ default: ({ children }: any) => <button>{children}</button> }));
vi.mock('@/components/Modal', () => ({ default: ({ children }: any) => <div>{children}</div> }));
vi.mock('@/components/HelpHint', () => ({ default: ({ children }: any) => <>{children}</> }));
vi.mock('@/components/ProfileHelpSheet', () => ({ default: () => null }));
vi.mock('@/hooks/use-mobile', () => ({ useIsMobile: () => false }));
vi.mock('@/components/ui/tooltip', () => ({ TooltipProvider: ({ children }: any) => <div>{children}</div> }));
vi.mock('@/components/ui/button', () => ({ Button: ({ children }: any) => <button>{children}</button> }));
vi.mock('@/components/ui/checkbox', () => ({ Checkbox: (props: any) => <input type="checkbox" {...props} /> }));

const therapyTypes = ['tablets', 'none'] as const;

describe.each(therapyTypes)('Profile for therapy type %s', (therapyType) => {
  it('omits insulin-specific inputs', () => {
    render(<Profile therapyType={therapyType} />);

    expect(screen.queryByLabelText('profileHelp.icr.title')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('profileHelp.preBolus.title')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('profileHelp.maxBolus.title')).not.toBeInTheDocument();
  });
});
