import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

const reminderTypes = {
  sugar: { label: 'Измерение сахара', icon: '🩸' },
  insulin: { label: 'Инсулин', icon: '💉' },
  meal: { label: 'Приём пищи', icon: '🍽️' },
  medicine: { label: 'Лекарства', icon: '💊' }
};

export interface ReminderFormValues {
  type: keyof typeof reminderTypes;
  title: string;
  time: string;
  interval?: string;
}

interface ReminderFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData?: ReminderFormValues;
  onSubmit: (values: ReminderFormValues) => void;
}

const ReminderForm = ({ open, onOpenChange, initialData, onSubmit }: ReminderFormProps) => {
  const [form, setForm] = useState<ReminderFormValues>({
    type: 'sugar',
    title: '',
    time: '',
    interval: ''
  });

  useEffect(() => {
    if (initialData) {
      setForm({ ...initialData, interval: initialData.interval || '' });
    } else {
      setForm({ type: 'sugar', title: '', time: '', interval: '' });
    }
  }, [initialData, open]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>
            {initialData ? 'Редактирование напоминания' : 'Новое напоминание'}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Тип напоминания
            </label>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(reminderTypes).map(([key, info]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setForm(prev => ({ ...prev, type: key as keyof typeof reminderTypes }))}
                  className={`p-3 rounded-lg border transition-all duration-200 ${
                    form.type === key
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:bg-secondary/50'
                  }`}
                >
                  <div className="text-lg mb-1">{info.icon}</div>
                  <div className="text-xs">{info.label}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Название
            </label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm(prev => ({ ...prev, title: e.target.value }))}
              className="medical-input"
              placeholder="Например: Измерение сахара"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Время
            </label>
            <input
              type="time"
              value={form.time}
              onChange={e => setForm(prev => ({ ...prev, time: e.target.value }))}
              className="medical-input"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="submit" className="medical-button flex-1">
              Сохранить
            </button>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="medical-button-secondary flex-1"
            >
              Отмена
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default ReminderForm;
