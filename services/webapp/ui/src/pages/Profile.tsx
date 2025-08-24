import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Save } from 'lucide-react';
import { MedicalHeader } from '@/components/MedicalHeader';
import { useToast } from '@/hooks/use-toast';
import MedicalButton from '@/components/MedicalButton';
import { getProfile, saveProfile } from '@/api/profile';
import { useTelegramContext } from '@/contexts/telegram-context';
import { Switch } from '@/components/ui/switch';

type ProfileField =
  | 'icr'
  | 'correctionFactor'
  | 'targetSugar'
  | 'lowThreshold'
  | 'highThreshold'
  | 'sosContact'
  | 'sosAlertsEnabled';

interface ProfileState {
  icr: string;
  correctionFactor: string;
  targetSugar: string;
  lowThreshold: string;
  highThreshold: string;
  sosContact: string;
  sosAlertsEnabled: boolean;
}

const Profile = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useTelegramContext();

  const [profile, setProfile] = useState<ProfileState>({
    icr: '',
    correctionFactor: '',
    targetSugar: '',
    lowThreshold: '',
    highThreshold: '',
    sosContact: '',
    sosAlertsEnabled: false,
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!user?.id) {
      return;
    }
    let active = true;
    const loadProfile = async () => {
      setIsLoading(true);
      try {
        const data = await getProfile(user.id);
        if (data && active) {
          setProfile({
            icr: String(data.icr ?? ''),
            correctionFactor: String(data.cf ?? ''),
            targetSugar: String(data.target ?? ''),
            lowThreshold: String(data.low ?? ''),
            highThreshold: String(data.high ?? ''),
            sosContact: String(data.sosContact ?? ''),
            sosAlertsEnabled: Boolean(data.sosAlertsEnabled ?? false),
          });
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        toast({
          title: 'Ошибка',
          description: message,
          variant: 'destructive',
        });
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };
    loadProfile();
    return () => {
      active = false;
    };
  }, [user?.id, toast]);

  const handleInputChange = (
    field: ProfileField,
    value: string | boolean,
  ) => {
    setProfile(prev => ({ ...prev, [field]: value } as ProfileState));
  };

  const handleSave = async () => {
    if (!user?.id) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось определить пользователя',
        variant: 'destructive',
      });
      return;
    }
    const icr = parseFloat(profile.icr);
    const cf = parseFloat(profile.correctionFactor);
    const target = parseFloat(profile.targetSugar);
    const low = parseFloat(profile.lowThreshold);
    const high = parseFloat(profile.highThreshold);

    if (![icr, cf, target, low, high].every(Number.isFinite)) {
      toast({
        title: 'Ошибка',
        description: 'Пожалуйста, введите корректные числовые значения',
        variant: 'destructive',
      });
      return;
    }

    try {
      await saveProfile({
        telegramId: user.id,
        icr,
        cf,
        target,
        low,
        high,
        sosContact: profile.sosContact || undefined,
        sosAlertsEnabled: profile.sosAlertsEnabled,
      });
      toast({
        title: 'Профиль сохранен',
        description: 'Ваши настройки успешно обновлены',
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader 
        title="Мой профиль" 
        showBack 
        onBack={() => navigate('/')}
      />
      
      <main className="container mx-auto px-4 py-6">
        {isLoading ? (
          <p className="text-center text-muted-foreground">Загрузка профиля...</p>
        ) : (
          <>
            <div className="medical-card animate-slide-up">
              <div className="space-y-6">
                {/* ICR */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    ICR (Инсулино-углеводное соотношение)
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.1"
                      value={profile.icr}
                      onChange={(e) => handleInputChange('icr', e.target.value)}
                      className="medical-input"
                      placeholder="12"
                    />
                    <span className="absolute right-3 top-3 text-muted-foreground text-sm">
                      г/ед.
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Сколько граммов углеводов покрывает 1 единица инсулина
                  </p>
                </div>

                {/* Коэффициент коррекции */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Коэффициент коррекции (КЧ)
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.1"
                      value={profile.correctionFactor}
                      onChange={(e) => handleInputChange('correctionFactor', e.target.value)}
                      className="medical-input"
                      placeholder="2.5"
                    />
                    <span className="absolute right-3 top-3 text-muted-foreground text-sm">
                      ммоль/л
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    На сколько снижает сахар 1 единица инсулина
                  </p>
                </div>

                {/* Целевой сахар */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Целевой уровень сахара
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.1"
                      value={profile.targetSugar}
                      onChange={(e) => handleInputChange('targetSugar', e.target.value)}
                      className="medical-input"
                      placeholder="6.0"
                    />
                    <span className="absolute right-3 top-3 text-muted-foreground text-sm">
                      ммоль/л
                    </span>
                  </div>
                </div>

                {/* Пороги */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Нижний порог
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        step="0.1"
                        value={profile.lowThreshold}
                        onChange={(e) => handleInputChange('lowThreshold', e.target.value)}
                        className="medical-input"
                        placeholder="4.0"
                      />
                      <span className="absolute right-3 top-3 text-muted-foreground text-xs">
                        ммоль/л
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Верхний порог
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        step="0.1"
                        value={profile.highThreshold}
                        onChange={(e) => handleInputChange('highThreshold', e.target.value)}
                        className="medical-input"
                        placeholder="10.0"
                      />
                      <span className="absolute right-3 top-3 text-muted-foreground text-xs">
                        ммоль/л
                      </span>
                    </div>
                  </div>
                </div>

                {/* SOS Contact */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    SOS контакт
                  </label>
                  <input
                    type="text"
                    value={profile.sosContact}
                    onChange={(e) => handleInputChange('sosContact', e.target.value)}
                    className="medical-input"
                    placeholder="+79998887766"
                  />
                </div>

                {/* SOS Alerts Toggle */}
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="sos-alerts"
                    className="block text-sm font-medium text-foreground"
                  >
                    Включить SOS-уведомления
                  </label>
                  <Switch
                    id="sos-alerts"
                    checked={profile.sosAlertsEnabled}
                    onCheckedChange={(checked) =>
                      handleInputChange('sosAlertsEnabled', checked)
                    }
                  />
                </div>

                {/* Кнопка сохранения */}
                <MedicalButton
                  onClick={handleSave}
                  className="w-full flex items-center justify-center gap-2"
                  size="lg"
                >
                  <Save className="w-4 h-4" />
                  Сохранить настройки
                </MedicalButton>
                {/* Дополнительные кнопки */}
                <div className="mt-4 space-y-2">
                  <MedicalButton
                    onClick={() => navigate('/history')}
                    className="w-full flex items-center justify-center gap-2"
                    size="lg"
                    variant="secondary"
                  >
                    📊 История
                  </MedicalButton>
                  <MedicalButton
                    onClick={() => navigate('/subscription')}
                    className="w-full flex items-center justify-center gap-2"
                    size="lg"
                    variant="secondary"
                  >
                    💳 Подписка
                  </MedicalButton>
                </div>
              </div>
            </div>

            {/* Дополнительная информация */}
            <div className="mt-6 medical-card">
              <h3 className="font-semibold text-foreground mb-3">Справка</h3>
              <div className="space-y-3 text-sm text-muted-foreground">
                <p>
                  <strong>ICR</strong> - показывает, сколько граммов углеводов покрывает 1 единица быстрого инсулина
                </p>
                <p><strong>КЧ</strong> - показывает, на сколько ммоль/л снижает уровень глюкозы 1 единица быстрого инсулина</p>
                <p>
                  Эти параметры индивидуальны и должны быть определены совместно с вашим врачом
                </p>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default Profile;
