import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MedicalHeader } from '@/components/MedicalHeader';
import MedicalButton from '@/components/MedicalButton';
import { useToast } from '@/hooks/use-toast';
import { updateRecord, HistoryRecord } from '@/api/history';

const NewMeasurement = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [sugar, setSugar] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const sugarValue = Number(sugar);
    if (isNaN(sugarValue) || sugarValue < 0 || sugarValue > 50) {
      toast({
        title: 'Ошибка',
        description: 'Уровень сахара должен быть от 0 до 50 ммоль/л',
        variant: 'destructive',
      });
      return;
    }
    const now = new Date();
    const record: HistoryRecord = {
      id: Date.now().toString(),
      date: new Date(now.toISOString().split('T')[0]),
      time: now.toTimeString().slice(0, 5),
      sugar: sugarValue,
      type: 'measurement',
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
              min="0"
              max="50"
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
