import { useEffect, useState } from 'react';

interface OnboardingStatus {
  completed: boolean;
  step: 'profile' | 'reminders' | null;
  missing: string[];
}

const steps: Array<{ key: 'profile' | 'reminders'; label: string }> = [
  { key: 'profile', label: 'Профиль' },
  { key: 'reminders', label: 'Напоминания' },
];

const OnboardingProgress = () => {
  const [data, setData] = useState<OnboardingStatus | null>(null);

  useEffect(() => {
    let active = true;
    import('@/shared/api/onboarding')
      .then((mod) => mod.getOnboardingStatus?.())
      .then((res) => {
        if (active && res) setData(res);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  if (!data) return null;

  if (data.completed) {
    return (
      <span className="text-xs px-2 py-1 rounded-full bg-medical-success/20 text-medical-success border border-medical-success/30">
        Завершено
      </span>
    );
  }

  const currentIndex = steps.findIndex((s) => s.key === data.step);

  return (
    <div className="flex items-center gap-2" aria-label="Onboarding progress">
      {steps.map((step, index) => {
        const done = index < currentIndex;
        const active = index === currentIndex;
        return (
          <div key={step.key} className="flex items-center gap-1">
            <div
              className={`w-4 h-4 rounded-full text-[10px] flex items-center justify-center ${
                done
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {done ? '✓' : index + 1}
            </div>
            <span
              className={`text-xs ${
                done || active ? 'text-foreground' : 'text-muted-foreground'
              }`}
            >
              {step.label}
            </span>
            {index < steps.length - 1 && (
              <span className="text-muted-foreground">→</span>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default OnboardingProgress;
