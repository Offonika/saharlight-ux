// Файл: webapp/ui/src/pages/Reminders.tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Clock, Edit2, Trash2, Bell } from 'lucide-react'
import { MedicalHeader } from '@/components/MedicalHeader'
import { useToast } from '@/hooks/use-toast'
import { getReminders, updateReminder, deleteReminder } from '@/api/reminders'
import { useTelegram } from '@/hooks/useTelegram'
import MedicalButton from '@/components/MedicalButton'
import { cn } from '@/lib/utils'
import { Reminder as ApiReminder } from '@sdk'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

type NormalizedReminderType = 'sugar' | 'insulin' | 'meal' | 'medicine'
type ReminderType = NormalizedReminderType | 'meds'

interface Reminder {
  id: number
  type: NormalizedReminderType
  title: string
  time: string   // "HH:MM"
  active: boolean
  interval?: number // stored in minutes
}

const TYPE_LABEL: Record<NormalizedReminderType, string> = {
  sugar: 'Измерение сахара',
  insulin: 'Инсулин',
  meal: 'Приём пищи',
  medicine: 'Лекарства',
}

const TYPE_ICON: Record<NormalizedReminderType, string> = {
  sugar: '🩸',
  insulin: '💉',
  meal: '🍽️',
  medicine: '💊',
}

const normalizeType = (t: ReminderType): NormalizedReminderType =>
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
          aria-label=
            {reminder.active ? 'Отключить напоминание' : 'Включить напоминание'}
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
  const { user, sendData } = useTelegram()

  const [reminders, setReminders] = useState<Reminder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dndNight, setDndNight] = useState(false)

  useEffect(() => {
    const value = localStorage.getItem('dnd-night')
    setDndNight(value === 'true')
  }, [])

  const handleToggleDndNight = (checked: boolean) => {
    setDndNight(checked)
    localStorage.setItem('dnd-night', checked ? 'true' : 'false')
    toast({
      title: 'Настройки обновлены',
      description: checked
        ? 'Не беспокоить ночью включено'
        : 'Не беспокоить ночью выключено',
    })
  }

  useEffect(() => {
    console.log('[Reminders] useEffect triggered, user:', user)
    
    if (!user?.id) {
      console.log('[Reminders] No user ID, stopping loading')
      setLoading(false) 
      setError(import.meta.env.MODE !== 'production' 
        ? 'Режим разработки: пользователь не загружен'
        : 'Пользователь не авторизован в Telegram'
      )
      return
    }
    
    let cancelled = false
    console.log('[Reminders] Loading reminders for user:', user.id)
    
    ;(async () => {
      try {
        const data = await getReminders(user.id)
        console.log('[Reminders] API response:', data)
        
        if (cancelled) return
        
        // Ensure data is an array before mapping
        const rawData = Array.isArray(data) ? data : [];
        const normalized: Reminder[] = rawData.map((r: ApiReminder) => {
          const nt = normalizeType(r.type as ReminderType)
          return {
            id: r.id ?? 0,
            type: nt,
            title: r.title ?? TYPE_LABEL[nt],
            time: r.time || '',
            active: r.isEnabled ?? false,
            interval: r.intervalHours != null ? r.intervalHours * 60 : undefined,
          }
        })
        normalized.sort((a, b) => parseTimeToMinutes(a.time) - parseTimeToMinutes(b.time))
        console.log('[Reminders] Normalized reminders:', normalized)
        setReminders(normalized)
        setError(null)
      } catch (err) {
        console.error('[Reminders] Error loading reminders:', err)
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Не удалось загрузить напоминания'
          setError(message)
          toast({ title: 'Ошибка', description: message, variant: 'destructive' })
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [toast, user?.id])

  const handleToggleReminder = async (id: number) => {
    if (!user?.id) return
    const prevReminders = [...reminders]
    const target = prevReminders.find(r => r.id === id)
    if (!target) return
    const nextActive = !target.active
    setReminders(prev =>
      prev.map(r => (r.id === id ? { ...r, active: nextActive } : r)),
    )
    try {
      await updateReminder({
        telegramId: user.id,
        id,
        type: target.type,
        time: target.time,
        intervalHours: target.interval != null ? target.interval / 60 : undefined,
        isEnabled: nextActive,
      })
      const hours = target.interval != null ? target.interval / 60 : undefined
      const value =
        hours != null && Number.isInteger(hours) ? `${hours}h` : target.time
      sendData({ id, type: target.type, value })
      toast({
        title: 'Напоминание обновлено',
        description: 'Статус напоминания изменён',
      })
    } catch (err) {
      setReminders(prevReminders)
      const message = err instanceof Error ? err.message : 'Не удалось обновить напоминание'
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      })
    }
  }

  const handleDeleteReminder = async (id: number) => {
    if (!user?.id) return
    const prevReminders = [...reminders]
    setReminders(prev => prev.filter(r => r.id !== id))
    try {
      await deleteReminder(user.id, id)
      toast({
        title: 'Напоминание удалено',
        description: 'Напоминание успешно удалено',
      })
    } catch (err) {
      setReminders(prevReminders)
      const message = err instanceof Error ? err.message : 'Не удалось удалить напоминание'
      toast({
        title: 'Ошибка',
        description: message,
        variant: 'destructive',
      })
    }
  }

  let content
  if (loading) {
    content = (
      <div className="space-y-3 mb-6">
        {Array.from({ length: 4 }).map((_, i) => <SkeletonItem key={i} />)}
      </div>
    )
  } else if (error) {
    content = (
      <div className="text-center py-12">
        <div className="text-destructive mb-4">{error}</div>
        {import.meta.env.MODE !== 'production' && (
          <div className="text-sm text-muted-foreground">
            <p>Для тестирования добавьте в localStorage:</p>
            <p className="font-mono text-xs mt-1">tg_init_data=user=%7B%22id%22%3A12345%2C%22first_name%22%3A%22Test%22%7D</p>
            <MedicalButton 
              variant="outline" 
              size="sm" 
              className="mt-4"
              onClick={() => {
                localStorage.setItem('tg_init_data', 'user=%7B%22id%22%3A12345%2C%22first_name%22%3A%22Test%22%7D');
                window.location.reload();
              }}
            >
              Включить тестовый режим
            </MedicalButton>
          </div>
        )}
      </div>
    )
  } else if (reminders.length === 0) {
    content = (
      <div className="text-center py-12">
        <Clock className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-lg font-medium text-foreground mb-2">Нет напоминаний</h3>
        <p className="text-muted-foreground mb-6">Добавьте первое напоминание для контроля диабета</p>
        <MedicalButton onClick={() => navigate('/reminders/new')} size="lg">
          Создать напоминание
        </MedicalButton>
      </div>
    )
  } else {
    content = (
      <div className="space-y-3 mb-6">
        {reminders.map((reminder, index) => (
          <ReminderRow
            key={reminder.id}
            reminder={reminder}
            index={index}
            onToggle={handleToggleReminder}
            onEdit={(r) => navigate(`/reminders/${r.id}/edit`, { state: r })}
            onDelete={handleDeleteReminder}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader title="Напоминания" showBack onBack={() => navigate('/')}> 
        <div className="flex items-center gap-1">
          <Switch
            id="dnd-night"
            checked={dndNight}
            onCheckedChange={handleToggleDndNight}
            aria-label="Не беспокоить ночью"
          />
          <Label htmlFor="dnd-night" className="text-sm">Тише ночью</Label>
        </div>
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
