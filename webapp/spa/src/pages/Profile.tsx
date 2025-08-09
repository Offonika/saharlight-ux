import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Save } from 'lucide-react';
import { MedicalHeader } from '@/components/MedicalHeader';
import { useTelegram } from '@/hooks/useTelegram';
import { useToast } from '@/hooks/use-toast';

const Profile = () => {
  const navigate = useNavigate();
  const { showMainButton, hideMainButton } = useTelegram();
  const { toast } = useToast();

  const [profile, setProfile] = useState({
    icr: '12',
    correctionFactor: '2.5',
    targetSugar: '6.0',
    lowThreshold: '4.0',
    highThreshold: '10.0'
  });

  const handleInputChange = (field: string, value: string) => {
    setProfile(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    // Здесь будет отправка данных на сервер
    toast({
      title: "Профиль сохранен",
      description: "Ваши настройки успешно обновлены"
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader 
        title="Мой профиль" 
        showBack 
        onBack={() => navigate('/')}
      />
      
      <main className="container mx-auto px-4 py-6">
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

            {/* Кнопка сохранения */}
            <button
              onClick={handleSave}
              className="medical-button w-full flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              Сохранить настройки
            </button>
          </div>
        </div>

        {/* Дополнительная информация */}
        <div className="mt-6 medical-card">
          <h3 className="font-semibold text-foreground mb-3">Справка</h3>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              <strong>ICR</strong> - показывает, сколько граммов углеводов покрывает 1 единица быстрого инсулина
            </p>
            <p>
              <strong>КЧ</strong> - показывает, на сколько ммоль/л снижает уровень глюкозы 1 единица быстрого инсулина
            </p>
            <p>
              Эти параметры индивидуальны и должны быть определены совместно с вашим врачом
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Profile;