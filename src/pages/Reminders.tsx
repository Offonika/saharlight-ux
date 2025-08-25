import RemindersList from '../features/reminders/pages/RemindersList'
import { MedicalHeader } from '@/components/MedicalHeader'
import { useNavigate } from 'react-router-dom'
import { useTelegram } from '@/hooks/useTelegram'
import { useState, useEffect } from 'react'
import { getPlanLimit } from '../features/reminders/hooks/usePlan'
import { useTelegramInitData } from '@/hooks/useTelegramInitData'

export default function Reminders() {
  const navigate = useNavigate()
  const { user } = useTelegram()
  const initData = useTelegramInitData()
  const [reminderCount, setReminderCount] = useState(0)
  const [planLimit, setPlanLimit] = useState(5)

  useEffect(() => {
    if (user?.id) {
      getPlanLimit(user.id, initData).then(setPlanLimit).catch(() => setPlanLimit(5))
    }
  }, [user?.id, initData])

  const quotaBadge = `${reminderCount}/${planLimit} 🔔`

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <MedicalHeader title={`Напоминания ${quotaBadge}`} showBack onBack={() => navigate('/')}>
        <a 
          href="/reminders/new" 
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg shadow-soft hover:shadow-medium hover:bg-primary/90 transition-all duration-200"
        >
          + Добавить
        </a>
      </MedicalHeader>

      <main className="container mx-auto px-4 py-6">
        <RemindersList onCountChange={setReminderCount} planLimit={planLimit} />
      </main>
    </div>
  )
}