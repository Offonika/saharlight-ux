import { useState } from 'react'
import { updateReminder } from '@/api/reminders'
import { useTelegram } from '@/hooks/useTelegram'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

export interface Reminder {
  id: number
  title: string
  type: string
  isEnabled: boolean
  lastFiredAt?: string | null
}

interface Props {
  reminders: Reminder[]
}

export default function RemindersList({ reminders: initial }: Props) {
  const [reminders, setReminders] = useState<Reminder[]>(initial)
  const { user } = useTelegram()
  const { toast } = useToast()

  const handleToggle = async (id: number) => {
    if (!user?.id) return
    const prev = [...reminders]
    const index = prev.findIndex(r => r.id === id)
    if (index === -1) return
    const nextValue = !prev[index].isEnabled
    const updated = prev.map(r =>
      r.id === id ? { ...r, isEnabled: nextValue } : r,
    )
    setReminders(updated)
    try {
      await updateReminder({ telegramId: user.id, id, isEnabled: nextValue } as any)
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
            {r.isEnabled && r.lastFiredAt && (
              <div className="text-xs text-muted-foreground">{r.lastFiredAt}</div>
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

