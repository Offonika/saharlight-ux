// Файл: webapp/ui/src/pages/Reminders.tsx
import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Clock, Edit2, Trash2, Bell } from 'lucide-react'
import { MedicalHeader } from '@/components/MedicalHeader'
import { useToast } from '@/hooks/use-toast'
import { getReminders, updateReminder, deleteReminder } from '@/api/reminders'
import MedicalButton from '@/components/MedicalButton'
import { cn } from '@/lib/utils'
import { Reminder as ApiReminder } from '@sdk'

type ReminderType = 'sugar' | 'insulin' | 'meal' | 'medicine' | 'meds'

interface Reminder {
  id: number
  type: ReminderType
  title: string
  time: string   // "HH:MM"
  active: boolean
  interval?: number
}

const TYPE_LABEL: Record<'sugar'|'insulin'|'meal'|'medicine', string> = {
  sugar: 'Измерение сахара',
  insulin: 'Инсулин',
  meal: 'Приём пищи',
  medicine: 'Лекарства',
}

const TYPE_ICON: Record<'sugar'|'insulin'|'meal'|'medicine', string> = {
  sugar: '🩸',
  insulin: '💉',
  meal: '🍽️',
  medicine: '💊',
}

const normalizeType = (t: ReminderType): 'sugar'|'insulin'|'meal'|'medicine' =>
  t === 'meds' ? 'medicine' : t

function parseTimeToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return (h || 0) * 60 + (m || 0)
}

function SkeletonItem() {
  return (
    <div className="rem-card animate-pulse">
      <div className="rem-left" />
      <div className="rem-main">
        <div className="h-5 w-40 rounded bg-muted/30" />
        <div className="rem-meta mt-1">
          <span className="h-6 w-16 rounded-full bg-muted/30" />
          <span className="h-6 w-28 rounded-full bg-muted/30" />
        </div>
      </div>
      <div className="rem-actions">
        <div className="icon-btn" />
        <div className="icon-btn" />
        <div className="icon-btn" />
      </div>
    </div>
  )
}

function ReminderRow({
  reminder,
  index,
  onToggle,
  onEdit,
  onDelete,
}: {
  reminder: Reminder
  index: number
  onToggle: (id: number) => void
  onEdit: (reminder: Reminder) => void
  onDelete: (id: number) => void
}) {
  const nt = normalizeType(reminder.type)
  const icon = TYPE_ICON[nt]
  const label = TYPE_LABEL[nt]

  return (
    <div
      className={cn('rem-card', !reminder.active && 'opacity-60')}
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="rem-left" aria-hidden>{icon}</div>

      <div className="rem-main">
        <div className="rem-title font-medium text-foreground">{reminder.title}</div>
        <div className="rem-meta">
          <span className="badge"><Clock className="inline -mt-0.5 mr-1 h-3 w-3" />{reminder.time}</span>
          <span className="badge badge-tonal">{label}</span>
        </div>
      </div>

      <div className="rem-actions">
        <MedicalButton
          size="icon"
          variant="ghost"
          className={cn(reminder.active ? 'bg-success/10 text-success' : 'bg-secondary text-muted-foreground')}
          onClick={() => onToggle(reminder.id)}
          aria-label={reminder.active ? 'Отключить напоминание' : 'Включить напоминание'}
        >
          <Bell className="w-4 h-4" />
        </MedicalButton>
        <MedicalButton
          size="icon"
          variant="ghost"
          onClick={() => onEdit(reminder)}
          aria-label="Редактировать"
        >
          <Edit2 className="w-4 h-4" />
        </MedicalButton>
        <MedicalButton
          size="icon"
          variant="destructive"
          onClick={() => onDelete(reminder.id)}
          aria-label="Удалить"
        >
          <Trash2 className="w-4 h-4" />
        </MedicalButton>
      </div>
    </div>
  )
}

export default function Reminders() {
  const navigate = useNavigate()
  const { toast } = useToast()

  const [reminders, setReminders] = useState<Reminder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await getReminders()
        if (cancelled) return
        const normalized: Reminder[] = (data || []).map((r: ApiReminder) => {
          const nt = normalizeType(r.type as ReminderType)
          return {
            id: r.id ?? 0,
            type: nt,
            title: TYPE_LABEL[nt],
            time: r.time || '',
            active: r.isEnabled ?? false,
            interval: r.intervalHours ?? undefined,
          }
        })
        normalized.sort((a, b) => parseTimeToMinutes(a.time) - parseTimeToMinutes(b.time))
        setReminders(normalized)
      } catch {
        if (!cancelled) {
          setError('Не удалось загрузить напоминания')
          toast({ title: 'Ошибка', description: 'Не удалось загрузить напоминания', variant: 'destructive' })
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [toast])

  const handleToggleReminder = async (id: number) => {
    const prevReminders = [...reminders]
    const target = prevReminders.find(r => r.id === id)
    if (!target) return
    const nextActive = !target.active
    setReminders(prev =>
      prev.map(r => (r.id === id ? { ...r, active: nextActive } : r)),
    )
    try {
      await updateReminder({
        telegramId: 1,
        id,
        type: target.type,
        time: target.time,
        intervalHours: target.interval,
        isEnabled: nextActive,
      })
      toast({
        title: 'Напоминание обновлено',
        description: 'Статус напоминания изменён',
      })
    } catch {
      setReminders(prevReminders)
      toast({
        title: 'Ошибка',
        description: 'Не удалось обновить напоминание',
        variant: 'destructive',
      })
    }
  }

  const handleDeleteReminder = async (id: number) => {
    const prevReminders = [...reminders]
    setReminders(prev => prev.filter(r => r.id !== id))
    try {
      await deleteReminder(1, id)
      toast({
        title: 'Напоминание удалено',
        description: 'Напоминание успешно удалено',
      })
    } catch {
      setReminders(prevReminders)
      toast({
        title: 'Ошибка',
        description: 'Не удалось удалить напоминание',
        variant: 'destructive',
      })
    }
  }

  const content = useMemo(() => {
    if (loading) {
      return (
        <div className="space-y-3 mb-6">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonItem key={i} />)}
        </div>
      )
    }
    if (error) return <div className="text-center py-12 text-destructive">{error}</div>
    if (reminders.length === 0) {
      return (
        <div className="text-center py-12">
          <Clock className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">Нет напоминаний</h3>
          <p className="text-muted-foreground mb-6">Добавьте первое напоминание для контроля диабета</p>
          <MedicalButton onClick={() => navigate('/reminders/new')} size="lg">
            Создать напоминание
          </MedicalButton>
        </div>
      )
    }
    return (
      <div className="space-y-3 mb-6">
        {reminders.map((reminder, index) => (
          <ReminderRow
            key={reminder.id}
            reminder={reminder}
            index={index}
            onToggle={handleToggleReminder}
            onEdit={(r) => navigate(`/reminders/${r.id}/edit`)}
            onDelete={handleDeleteReminder}
          />
        ))}
      </div>
    )
  }, [loading, error, reminders, navigate])

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader title="Напоминания" showBack onBack={() => navigate('/')}>
        <MedicalButton
          size="icon"
          onClick={() => navigate('/reminders/new')}
          className="bg-primary text-primary-foreground hover:bg-primary/90 border-0"
          aria-label="Добавить напоминание"
        >
          <Plus className="w-5 h-5" />
        </MedicalButton>
      </MedicalHeader>

      <main className="container mx-auto px-4 py-6">
        {content}
      </main>
    </div>
  )
}
