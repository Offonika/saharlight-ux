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
        <form onSubmit={handleSubmit} className="medical-card p-4 flex flex-col gap-4">
          <label className="text-sm font-medium">
            Уровень сахара
            <input
              type="number"
              step="0.1"
              className="medical-input mt-2"
              value={sugar}
              onChange={(e) => setSugar(e.target.value)}
              placeholder="ммоль/л"
            />
          </label>
          <MedicalButton
            type="submit"
            className="w-full"
            disabled={!sugar}
            size="lg"
          >
            Сохранить
          </MedicalButton>
        </form>
      </main>
    </div>
  );
};

export default NewMeasurement;
