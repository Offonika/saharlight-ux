// Файл: webapp/ui/src/pages/Reminders.tsx
import { useState, useEffect, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Clock, Edit2, Trash2, Bell } from 'lucide-react'
import { MedicalHeader } from '@/components/MedicalHeader'
import { useToast } from '@/hooks/use-toast'
import { getReminders, updateReminder, deleteReminder } from '@/api/reminders'
import MedicalButton from '@/components/MedicalButton'
import { useTelegramContext } from '@/contexts/TelegramContext'
import { cn } from '@/lib/utils'
import {
  normalizeReminderType,
  type ReminderType,
  type NormalizedReminderType,
} from '@/lib/reminders'
import { Reminder as ApiReminder } from '@sdk'

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

function parseTimeToMinutes(t: string): number {
  const match = /^(\d{1,2}):(\d{2})$/.exec(t)
  if (!match) return NaN
  const h = Number(match[1])
  const m = Number(match[2])
  if (h > 23 || m > 59) return NaN
  return h * 60 + m
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
  const nt = normalizeReminderType(reminder.type)
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
  const { user, sendData, isReady } = useTelegramContext()

  const [reminders, setReminders] = useState<Reminder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ReactNode | null>(null)

  useEffect(() => {
    if (!isReady) return
    if (!user?.id) {
      setLoading(false)
      setError(
        <div className="space-y-4">
          <p className="text-destructive">Не удалось получить данные пользователя.</p>
          <div className="flex flex-col items-center gap-2">
            <MedicalButton onClick={() => window.location.reload()}>Повторить</MedicalButton>
            <MedicalButton asChild variant="outline">
              <a
                href={`https://t.me/${import.meta.env.VITE_TELEGRAM_BOT}?startapp=reminders`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Открыть в Telegram
              </a>
            </MedicalButton>
          </div>
        </div>,
      )
      return
    }
    setLoading(true)
    setError(null)
    let cancelled = false
    ;(async () => {
      try {
        const data = await getReminders(user.id)
        if (cancelled) return
        const normalized: Reminder[] = (data || []).map((r: ApiReminder) => {
          const nt = normalizeReminderType(r.type as ReminderType)
          return {
            id: r.id ?? 0,
            type: nt,
            title: r.title ?? TYPE_LABEL[nt],
            time: r.time || '',
            active: r.isEnabled ?? false,
            interval: r.intervalHours != null ? r.intervalHours * 60 : undefined,
          }
        })
        const invalid = normalized.filter(r => Number.isNaN(parseTimeToMinutes(r.time)))
        if (invalid.length > 0) {
          toast({
            title: 'Ошибка',
            description: `Некорректное время напоминания: ${invalid.map(r => r.time).join(', ')}`,
            variant: 'destructive',
          })
        }
        normalized.sort((a, b) => {
          const ta = parseTimeToMinutes(a.time)
          const tb = parseTimeToMinutes(b.time)
          if (Number.isNaN(ta) && Number.isNaN(tb)) return 0
          if (Number.isNaN(ta)) return 1
          if (Number.isNaN(tb)) return -1
          return ta - tb
        })
        setReminders(normalized)
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Не удалось загрузить напоминания'
          setError(<p className="text-destructive mb-4">{message}</p>)
          toast({ title: 'Ошибка', description: message, variant: 'destructive' })
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [toast, user?.id, isReady])

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
    content = <div className="text-center py-12">{error}</div>
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
