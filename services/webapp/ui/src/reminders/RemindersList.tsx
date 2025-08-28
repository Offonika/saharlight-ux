import { useState } from 'react'
import { useTelegram } from '@/hooks/useTelegram'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'
import { mockApi } from '@/api/mock-server'
import { useRemindersApi } from '@/features/reminders/api/reminders'
import type { ReminderSchema } from '@sdk'

export interface Reminder {
  id: number
  telegramId: number
  type: string
  title?: string | null
  kind: 'at_time' | 'every' | 'after_event'
  time?: string | null
  intervalMinutes?: number | null
  minutesAfter?: number | null
  daysOfWeek?: number[] | Set<number> | null
  isEnabled: boolean
  nextAt?: string | null
}

interface Props {
  reminders: Reminder[]
}

export default function RemindersList({ reminders: initial }: Props) {
  const [reminders, setReminders] = useState<Reminder[]>(initial)
  const { user } = useTelegram()
  const { toast } = useToast()
  const api = useRemindersApi()

  const handleToggle = async (id: number) => {
    if (!user?.id) return
    const prev = [...reminders]
    const index = prev.findIndex(r => r.id === id)
    if (index === -1) return
    const current = prev[index]
    const nextValue = !current.isEnabled
    const updated = prev.map(r =>
      r.id === id
        ? { ...r, isEnabled: nextValue, nextAt: nextValue ? r.nextAt : undefined }
        : r,
    )
    setReminders(updated)
    try {
      try {
        const reminder: ReminderSchema = {
          telegramId: current.telegramId,
          id: current.id,
          type: current.type as any,
          kind: current.kind,
          time: current.time ?? undefined,
          intervalMinutes: current.intervalMinutes ?? undefined,
          minutesAfter: current.minutesAfter ?? undefined,
          daysOfWeek: current.daysOfWeek ?? undefined,
          isEnabled: nextValue,
        }
        await api.remindersPatch({ reminder })
      } catch (apiError) {
        console.warn('Backend API failed, using mock API:', apiError)
        await mockApi.updateReminder({ ...current, isEnabled: nextValue })
      }
    } catch (error) {
      setReminders(prev)
      const message =
        error instanceof Error ? error.message : 'Не удалось обновить напоминание'
      toast({ title: 'Ошибка', description: message, variant: 'destructive' })
    }
  }

  return (
    <div className="space-y-2">
      {reminders.map(r => (
        <div
          key={r.id}
          className={cn(
            'flex items-center justify-between p-3 border rounded',
            !r.isEnabled && 'opacity-60',
          )}
        >
          <div>
            <div className="font-medium">{r.title}</div>
            {r.isEnabled && r.nextAt && (
              <div className="text-xs text-muted-foreground">{r.nextAt}</div>
            )}
          </div>
          <button
            className="px-2 py-1 text-sm border rounded"
            onClick={() => handleToggle(r.id)}
          >
            {r.isEnabled ? 'Выключить' : 'Включить'}
          </button>
        </div>
      ))}
    </div>
  )
}

