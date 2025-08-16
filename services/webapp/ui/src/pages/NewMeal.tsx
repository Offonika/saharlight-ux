import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MedicalHeader } from '@/components/MedicalHeader';
import MedicalButton from '@/components/MedicalButton';
import { useToast } from '@/hooks/use-toast';
import { updateRecord, HistoryRecord } from '@/api/history';

const NewMeal = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [meal, setMeal] = useState('');
  const [carbs, setCarbs] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const now = new Date();
    const record: HistoryRecord = {
      id: Date.now().toString(),
      date: now.toISOString().split('T')[0],
      time: now.toTimeString().slice(0, 5),
      type: 'meal',
      notes: meal,
      carbs: Number(carbs),
    };
    try {
      await updateRecord(record);
      navigate('/history');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Неизвестная ошибка';
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
          <MedicalButton
            type="submit"
            className="w-full"
            disabled={!meal || !carbs}
            size="lg"
          >
            Сохранить
          </MedicalButton>
        </form>
      </main>
    </div>
  );
};

export default NewMeal;
