import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MedicalHeader } from '@/components/MedicalHeader';
import MedicalButton from '@/components/MedicalButton';

const NewMeal = () => {
  const navigate = useNavigate();
  const [meal, setMeal] = useState('');
  const [carbs, setCarbs] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/history');
  };

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader
        title="Добавить еду"
        showBack
        onBack={() => navigate(-1)}
      />
      <main className="container mx-auto px-4 py-6">
        <form onSubmit={handleSubmit} className="medical-card bg-gradient-success/5 border-medical-success/20 animate-slide-up">
          <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Название блюда
            </label>
            <input
              className="medical-input"
              value={meal}
              onChange={(e) => setMeal(e.target.value)}
              placeholder="Например: овсянка с молоком"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Углеводы (г)
            </label>
            <input
              type="number"
              step="0.1"
              className="medical-input"
              value={carbs}
              onChange={(e) => setCarbs(e.target.value)}
              placeholder="Введите количество углеводов"
            />
          </div>
          
          <MedicalButton
            type="submit"
            className="w-full"
            variant="success"
            disabled={!meal || !carbs}
            size="lg"
          >
            Сохранить блюдо
          </MedicalButton>
        </div>
        </form>
      </main>
    </div>
  );
};

export default NewMeal;
