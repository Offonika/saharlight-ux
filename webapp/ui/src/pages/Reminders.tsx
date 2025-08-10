import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Clock, Edit2, Trash2, Bell } from 'lucide-react';
import { MedicalHeader } from '@/components/MedicalHeader';
import { useToast } from '@/hooks/use-toast';
import ReminderForm, { ReminderFormValues } from '@/components/ReminderForm';
import { createReminder, updateReminder, getReminders } from '@/api/reminders';
import MedicalButton from '@/components/MedicalButton';
import { cn } from '@/lib/utils';

interface Reminder {
  id: number;
  type: 'sugar' | 'insulin' | 'meal' | 'medicine';
  title: string;
  time: string;
  active: boolean;
  interval?: number;
}

const reminderTypes = {
  sugar: { label: 'Измерение сахара', icon: '🩸', color: 'medical-error' },
  insulin: { label: 'Инсулин', icon: '💉', color: 'medical-blue' },
  meal: { label: 'Приём пищи', icon: '🍽️', color: 'medical-success' },
  medicine: { label: 'Лекарства', icon: '💊', color: 'medical-teal' }
};

interface ReminderItemProps {
  reminder: Reminder;
  index: number;
  onToggle: (id: number) => void;
  onEdit: (reminder: Reminder) => void;
  onDelete: (id: number) => void;
}

const ReminderItem = ({
  reminder,
  index,
  onToggle,
  onEdit,
  onDelete
}: ReminderItemProps) => {
  const typeInfo = reminderTypes[reminder.type];
  return (
    <div
      className={cn('rem-card', !reminder.active && 'opacity-60')}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="flex items-center justify-between">
        <div className="rem-main">
          <div
            className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center',
              typeInfo.color === 'medical-error'
                ? 'bg-medical-error/10'
                : typeInfo.color === 'medical-blue'
                  ? 'bg-medical-blue/10'
                  : typeInfo.color === 'medical-success'
                    ? 'bg-medical-success/10'
                    : 'bg-medical-teal/10'
            )}
          >
            <span className="text-lg">{typeInfo.icon}</span>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="rem-title font-medium text-foreground">
              {reminder.title}
            </h3>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
              <Clock className="w-3 h-3" />
              <span className="badge">{reminder.time}</span>
              <span className="badge badge-tonal">{typeInfo.label}</span>
            </div>
          </div>
        </div>
        <div className="rem-actions">
          <button
            type="button"
            className={cn(
              'icon-btn',
              reminder.active
                ? 'bg-success/10 text-success'
                : 'bg-secondary text-muted-foreground'
            )}
            onClick={() => onToggle(reminder.id)}
            aria-label={
              reminder.active
                ? 'Отключить напоминание'
                : 'Включить напоминание'
            }
          >
            <Bell className="w-4 h-4" />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={() => onEdit(reminder)}
            aria-label="Редактировать"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={() => onDelete(reminder.id)}
            aria-label="Удалить"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

const Reminders = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReminders = async () => {
      try {
        const data = await getReminders();
        setReminders(data);
      } catch {
        setError('Не удалось загрузить напоминания');
        toast({
          title: 'Ошибка',
          description: 'Не удалось загрузить напоминания',
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };
    fetchReminders();
  }, [toast]);


  const [formOpen, setFormOpen] = useState(false);
  const [editingReminder, setEditingReminder] = useState<Reminder | null>(null);

  const handleToggleReminder = (id: number) => {
    setReminders(prev => 
      prev.map(reminder => 
        reminder.id === id 
          ? { ...reminder, active: !reminder.active }
          : reminder
      )
    );
    toast({
      title: "Напоминание обновлено",
      description: "Статус напоминания изменен"
    });
  };

  const handleDeleteReminder = (id: number) => {
    setReminders(prev => prev.filter(reminder => reminder.id !== id));
    toast({
      title: "Напоминание удалено",
      description: "Напоминание успешно удалено"
    });
  };

  const handleSaveReminder = async (values: ReminderFormValues) => {
    try {
      if (editingReminder) {
        await updateReminder({ id: editingReminder.id, ...values });
        setReminders(prev =>
          prev.map(r =>
            r.id === editingReminder.id ? { ...r, ...values } : r
          )
        );
        toast({
          title: 'Напоминание обновлено',
          description: 'Изменения сохранены'
        });
      } else {
        const data = await createReminder(values);
        setReminders(prev => [
          ...prev,
          { id: Number(data.id), ...values, active: true }
        ]);
        toast({
          title: 'Напоминание добавлено',
          description: 'Новое напоминание создано'
        });
      }
      setFormOpen(false);
      setEditingReminder(null);
    } catch {
      toast({
        title: 'Ошибка',
        description: 'Не удалось сохранить напоминание',
        variant: 'destructive'
      });
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader 
        title="Напоминания" 
        showBack 
        onBack={() => navigate('/')}
      >
        <MedicalButton
          variant="icon"
          onClick={() => {
            setEditingReminder(null);
            setFormOpen(true);
          }}
          className="bg-primary text-primary-foreground hover:bg-primary/90 border-0"
          aria-label="Добавить напоминание"
        >
          <Plus className="w-5 h-5" />
        </MedicalButton>
      </MedicalHeader>
      
      <main className="container mx-auto px-4 py-6">

        {loading ? (
          <div className="text-center py-12">Загрузка...</div>
        ) : error ? (
          <div className="text-center py-12 text-destructive">{error}</div>
        ) : (
          <div className="space-y-3 mb-6">
          {reminders.map((reminder, index) => {
            const typeInfo = reminderTypes[reminder.type];
            return (
              <div
                key={reminder.id}
                className={`medical-list-item ${!reminder.active ? 'opacity-60' : ''}`}
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      typeInfo.color === 'medical-error' ? 'bg-medical-error/10' :
                      typeInfo.color === 'medical-blue' ? 'bg-medical-blue/10' :
                      typeInfo.color === 'medical-success' ? 'bg-medical-success/10' :
                      'bg-medical-teal/10'
                    }`}>
                      <span className="text-lg">{typeInfo.icon}</span>
                    </div>
                    <div className="flex-1">
                      <h3 className="font-medium text-foreground">{reminder.title}</h3>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        <span>{reminder.time}</span>
                        <span className="text-xs bg-secondary px-2 py-1 rounded">
                          {typeInfo.label}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <MedicalButton
                      variant="icon"
                      onClick={() => handleToggleReminder(reminder.id)}
                      className={cn(
                        'border-0',
                        reminder.active
                          ? 'bg-success/10 text-success'
                          : 'bg-secondary text-muted-foreground'
                      )}
                      aria-label={reminder.active ? 'Отключить напоминание' : 'Включить напоминание'}
                    >
                      <Bell className="w-4 h-4" />
                    </MedicalButton>
                    <MedicalButton
                      variant="icon"
                      onClick={() => {
                        setEditingReminder(reminder);
                        setFormOpen(true);
                      }}
                      className="bg-transparent hover:bg-secondary text-muted-foreground border-0"
                      aria-label="Редактировать"
                    >
                      <Edit2 className="w-4 h-4" />
                    </MedicalButton>
                    <MedicalButton
                      variant="icon"
                      onClick={() => handleDeleteReminder(reminder.id)}
                      className="bg-transparent hover:bg-destructive/10 hover:text-destructive text-muted-foreground border-0"
                      aria-label="Удалить"
                    >
                      <Trash2 className="w-4 h-4" />
                    </MedicalButton>
                  </div>
                </div>
              </div>
            );
          })}
          </div>
        )}


        {/* Форма создания/редактирования */}
        <ReminderForm
          open={formOpen}
          onOpenChange={(open) => {
            setFormOpen(open);
            if (!open) setEditingReminder(null);
          }}
          initialData={editingReminder || undefined}
          onSubmit={handleSaveReminder}
        />

        {/* Пустое состояние */}
        {!loading && !error && reminders.length === 0 && (
          <div className="text-center py-12">
            <Clock className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">
              Нет напоминаний
            </h3>
            <p className="text-muted-foreground mb-6">
              Добавьте первое напоминание для контроля диабета
            </p>
            <MedicalButton
              onClick={() => {
                setEditingReminder(null);
                setFormOpen(true);
              }}
              size="lg"
            >
              Создать напоминание
            </MedicalButton>
          </div>
        )}
      </main>
    </div>
  );
};

export default Reminders;
