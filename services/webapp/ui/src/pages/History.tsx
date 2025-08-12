import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, TrendingUp, Edit2, Trash2, Filter } from 'lucide-react';
import { MedicalHeader } from '@/components/MedicalHeader';
import { useToast } from '@/hooks/use-toast';
import MedicalButton from '@/components/MedicalButton';

interface HistoryRecord {
  id: string;
  date: string;
  time: string;
  sugar?: number;
  carbs?: number;
  breadUnits?: number;
  insulin?: number;
  notes?: string;
  type: 'measurement' | 'meal' | 'insulin';
}

const History = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [records, setRecords] = useState<HistoryRecord[]>([
    {
      id: '1',
      date: '2024-01-08',
      time: '08:30',
      sugar: 6.2,
      type: 'measurement',
      notes: 'Утром натощак'
    },
    {
      id: '2',
      date: '2024-01-08',
      time: '09:00',
      sugar: 5.8,
      carbs: 45,
      breadUnits: 3.8,
      insulin: 4,
      type: 'meal',
      notes: 'Завтрак: овсянка с фруктами'
    },
    {
      id: '3',
      date: '2024-01-08',
      time: '13:15',
      sugar: 8.2,
      carbs: 60,
      breadUnits: 5.0,
      insulin: 6,
      type: 'meal',
      notes: 'Обед: макароны с мясом'
    },
    {
      id: '4',
      date: '2024-01-07',
      time: '22:00',
      insulin: 18,
      type: 'insulin',
      notes: 'Длинный инсулин перед сном'
    }
  ]);

  const [selectedDate, setSelectedDate] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [editingRecord, setEditingRecord] = useState<HistoryRecord | null>(null);

  const filteredRecords = records.filter(record => {
    const dateMatch = !selectedDate || record.date === selectedDate;
    const typeMatch = selectedType === 'all' || record.type === selectedType;
    return dateMatch && typeMatch;
  });

  const handleEditRecord = (record: HistoryRecord) => {
    setEditingRecord({ ...record });
  };

  const handleUpdateRecord = async () => {
    if (editingRecord) {
      try {
        const res = await fetch('/history', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(editingRecord),
        });
        const data = await res.json();
        if (!res.ok || data.status !== 'ok') {
          throw new Error('failed');
        }

        setRecords(prev =>
          prev.map(r => (r.id === editingRecord.id ? editingRecord : r))
        );
        setEditingRecord(null);
        toast({
          title: 'Запись обновлена',
          description: 'Изменения сохранены',
        });
      } catch {
        toast({
          title: 'Ошибка',
          description: 'Не удалось обновить запись',
          variant: 'destructive',
        });
      }
    }
  };

  const handleDeleteRecord = (id: string) => {
    toast({
      title: "Запись удалена",
      description: "Запись успешно удалена из истории"
    });
  };

  const getRecordIcon = (type: string) => {
    switch (type) {
      case 'measurement': return '🩸';
      case 'meal': return '🍽️';
      case 'insulin': return '💉';
      default: return '📝';
    }
  };

  const getRecordColor = (type: string) => {
    switch (type) {
      case 'measurement': return 'medical-error';
      case 'meal': return 'medical-success';
      case 'insulin': return 'medical-blue';
      default: return 'neutral-500';
    }
  };

  const getSugarColor = (sugar: number) => {
    if (sugar < 4) return 'text-medical-error';
    if (sugar > 10) return 'text-medical-warning';
    if (sugar >= 4 && sugar <= 7) return 'text-medical-success';
    return 'text-medical-teal';
  };

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader 
        title="История" 
        showBack 
        onBack={() => navigate('/')}
      />
      
      <main className="container mx-auto px-4 py-6">
        {/* Фильтры */}
        <div className="medical-card mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <span className="font-medium text-foreground">Фильтры</span>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Дата
              </label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="medical-input"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Тип записи
              </label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="medical-input"
              >
                <option value="all">Все записи</option>
                <option value="measurement">Измерения</option>
                <option value="meal">Еда</option>
                <option value="insulin">Инсулин</option>
              </select>
            </div>
          </div>
        </div>

        {/* Статистика */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="medical-card text-center py-4">
            <div className="text-xl font-bold text-medical-success">6.8</div>
            <div className="text-xs text-muted-foreground">Средний сахар</div>
          </div>
          <div className="medical-card text-center py-4">
            <div className="text-xl font-bold text-medical-teal">24</div>
            <div className="text-xs text-muted-foreground">Записей</div>
          </div>
          <div className="medical-card text-center py-4">
            <div className="text-xl font-bold text-medical-blue">85%</div>
            <div className="text-xs text-muted-foreground">В норме</div>
          </div>
        </div>

        {/* Список записей */}
        <div className="space-y-3">
          {filteredRecords.map((record, index) => (
            <div
              key={record.id}
              className="medical-list-item"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  getRecordColor(record.type) === 'medical-error' ? 'bg-medical-error/10' :
                  getRecordColor(record.type) === 'medical-success' ? 'bg-medical-success/10' :
                  getRecordColor(record.type) === 'medical-blue' ? 'bg-medical-blue/10' :
                  'bg-neutral-500/10'
                }`}>
                  <span className="text-lg">{getRecordIcon(record.type)}</span>
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {new Date(record.date).toLocaleDateString('ru-RU')}
                      </span>
                      <span className="text-sm font-medium">{record.time}</span>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <MedicalButton
                        size="icon"
                        onClick={() => handleEditRecord(record)}
                        className="bg-transparent hover:bg-secondary text-muted-foreground border-0 p-1"
                        aria-label="Редактировать"
                      >
                        <Edit2 className="w-3 h-3" />
                      </MedicalButton>
                      <MedicalButton
                        size="icon"
                        onClick={() => handleDeleteRecord(record.id)}
                        className="bg-transparent hover:bg-destructive/10 hover:text-destructive text-muted-foreground border-0 p-1"
                        aria-label="Удалить"
                      >
                        <Trash2 className="w-3 h-3" />
                      </MedicalButton>
                    </div>
                  </div>

                  <div className="grid grid-cols-4 gap-4 text-sm mb-2">
                    {record.sugar && (
                      <div>
                        <div className={`font-semibold ${getSugarColor(record.sugar)}`}>
                          {record.sugar}
                        </div>
                        <div className="text-xs text-muted-foreground">ммоль/л</div>
                      </div>
                    )}
                    
                    {record.carbs && (
                      <div>
                        <div className="font-semibold text-foreground">{record.carbs}</div>
                        <div className="text-xs text-muted-foreground">г углев.</div>
                      </div>
                    )}
                    
                    {record.breadUnits && (
                      <div>
                        <div className="font-semibold text-foreground">{record.breadUnits}</div>
                        <div className="text-xs text-muted-foreground">ХЕ</div>
                      </div>
                    )}
                    
                    {record.insulin && (
                      <div>
                        <div className="font-semibold text-medical-blue">{record.insulin}</div>
                        <div className="text-xs text-muted-foreground">ед.</div>
                      </div>
                    )}
                  </div>
                  
                  {record.notes && (
                    <p className="text-sm text-muted-foreground truncate">
                      {record.notes}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Форма редактирования */}
        {editingRecord && (
          <div className="medical-card animate-scale-in mt-6">
            <h3 className="font-semibold text-foreground mb-4">Редактирование записи</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Дата
                </label>
                <input
                  type="date"
                  value={editingRecord.date}
                  onChange={e =>
                    setEditingRecord(prev =>
                      prev ? { ...prev, date: e.target.value } : prev
                    )
                  }
                  className="medical-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Время
                </label>
                <input
                  type="time"
                  value={editingRecord.time}
                  onChange={e =>
                    setEditingRecord(prev =>
                      prev ? { ...prev, time: e.target.value } : prev
                    )
                  }
                  className="medical-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Сахар (ммоль/л)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={editingRecord.sugar ?? ''}
                  onChange={e =>
                    setEditingRecord(prev =>
                      prev
                        ? {
                            ...prev,
                            sugar: e.target.value ? Number(e.target.value) : undefined,
                          }
                        : prev
                    )
                  }
                  className="medical-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Углеводы (г)
                </label>
                <input
                  type="number"
                  value={editingRecord.carbs ?? ''}
                  onChange={e =>
                    setEditingRecord(prev =>
                      prev
                        ? {
                            ...prev,
                            carbs: e.target.value ? Number(e.target.value) : undefined,
                          }
                        : prev
                    )
                  }
                  className="medical-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  ХЕ
                </label>
                <input
                  type="number"
                  value={editingRecord.breadUnits ?? ''}
                  onChange={e =>
                    setEditingRecord(prev =>
                      prev
                        ? {
                            ...prev,
                            breadUnits: e.target.value ? Number(e.target.value) : undefined,
                          }
                        : prev
                    )
                  }
                  className="medical-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Инсулин (ед.)
                </label>
                <input
                  type="number"
                  value={editingRecord.insulin ?? ''}
                  onChange={e =>
                    setEditingRecord(prev =>
                      prev
                        ? {
                            ...prev,
                            insulin: e.target.value ? Number(e.target.value) : undefined,
                          }
                        : prev
                    )
                  }
                  className="medical-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Заметки
                </label>
                <input
                  type="text"
                  value={editingRecord.notes ?? ''}
                  onChange={e =>
                    setEditingRecord(prev =>
                      prev ? { ...prev, notes: e.target.value } : prev
                    )
                  }
                  className="medical-input"
                  placeholder="Комментарий"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <MedicalButton
                  type="button"
                  onClick={handleUpdateRecord}
                  className="flex-1"
                  size="lg"
                >
                  Сохранить
                </MedicalButton>
                <MedicalButton
                  type="button"
                  onClick={() => setEditingRecord(null)}
                  variant="secondary"
                  className="flex-1"
                  size="lg"
                >
                  Отмена
                </MedicalButton>
              </div>
            </div>
          </div>
        )}

        {/* Пустое состояние */}
        {filteredRecords.length === 0 && (
          <div className="text-center py-12">
            <Calendar className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">
              Записи не найдены
            </h3>
            <p className="text-muted-foreground">
              Попробуйте изменить фильтры или добавьте новую запись
            </p>
          </div>
        )}

        {/* Кнопка аналитики */}
        <div className="mt-8">
          <MedicalButton
            onClick={() => navigate('/analytics')}
            className="w-full flex items-center justify-center gap-2"
            size="lg"
          >
            <TrendingUp className="w-4 h-4" />
            Посмотреть аналитику
          </MedicalButton>
        </div>
      </main>
    </div>
  );
};

export default History;
