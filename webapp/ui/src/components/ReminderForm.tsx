import { useEffect, useState } from 'react';
import { Modal, SegmentedControl } from '@/components';
import { Button } from '@/components/ui/button';

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

  const isDisabled = !form.title || !form.time;

  const footer = (
    <div className="flex gap-3">
      <Button
        type="submit"
        form="reminder-form"
        className="flex-1"
        disabled={isDisabled}
        size="lg"
      >
        Сохранить
      </Button>
      <Button
        type="button"
        onClick={() => onOpenChange(false)}
        variant="secondary"
        className="flex-1"
        size="lg"
      >
        Отмена
      </Button>
    </div>
  );

  const segmentedItems = Object.entries(reminderTypes).map(([key, info]) => ({
    value: key,
    icon: info.icon,
    label: info.label
  }));

  return (
    <Modal
      open={open}
      onClose={() => onOpenChange(false)}
      title={initialData ? 'Редактирование напоминания' : 'Новое напоминание'}
      footer={footer}
    >
      <form id="reminder-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Тип напоминания
          </label>
          <SegmentedControl
            value={form.type}
            onChange={value =>
              setForm(prev => ({ ...prev, type: value as keyof typeof reminderTypes }))
            }
            items={segmentedItems}
          />
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
      </form>
    </Modal>
  );
};

export default ReminderForm;
