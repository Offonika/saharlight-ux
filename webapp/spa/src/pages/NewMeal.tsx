import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MedicalHeader } from '@/components/MedicalHeader';

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
        <form onSubmit={handleSubmit} className="medical-card p-4 flex flex-col gap-4">
          <label className="text-sm font-medium">
            Название блюда
            <input
              className="medical-input mt-2"
              value={meal}
              onChange={(e) => setMeal(e.target.value)}
              placeholder="Например: овсянка"
            />
          </label>
          <label className="text-sm font-medium">
            Углеводы (г)
            <input
              type="number"
              className="medical-input mt-2"
              value={carbs}
              onChange={(e) => setCarbs(e.target.value)}
            />
          </label>
          <button type="submit" className="medical-button w-full">
            Сохранить
          </button>
        </form>
      </main>
    </div>
  );
};

export default NewMeal;
