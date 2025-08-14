import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MedicalHeader } from '@/components/MedicalHeader';
import MedicalButton from '@/components/MedicalButton';

const NewMeasurement = () => {
  const navigate = useNavigate();
  const [sugar, setSugar] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/history');
  };

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader
        title="Запись сахара"
        showBack
        onBack={() => navigate(-1)}
      />
      <main className="container mx-auto px-4 py-6">
        <form onSubmit={handleSubmit} className="medical-card bg-gradient-warning/5 border-medical-error/20 animate-slide-up">
          <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Уровень сахара в крови
            </label>
            <div className="relative">
              <input
                type="number"
                step="0.1"
                className="medical-input pr-20"
                value={sugar}
                onChange={(e) => setSugar(e.target.value)}
                placeholder="Введите показания глюкометра"
              />
              <span className="absolute right-3 top-3 text-muted-foreground text-sm">
                ммоль/л
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Нормальные значения: 4.0 - 7.0 ммоль/л
            </p>
          </div>
          
          <MedicalButton
            type="submit"
            className="w-full"
            variant="warning"
            disabled={!sugar}
            size="lg"
          >
            Сохранить измерение
          </MedicalButton>
        </div>
        </form>
      </main>
    </div>
  );
};

export default NewMeasurement;
