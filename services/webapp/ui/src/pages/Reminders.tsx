import RemindersList from '../features/reminders/pages/RemindersList'
import { MedicalHeader } from '@/components/MedicalHeader'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { postOnboardingEvent } from '@/api/onboarding'

export default function Reminders() {
  const navigate = useNavigate()
  const [reminderCount, setReminderCount] = useState(0)
  const [planLimit, setPlanLimit] = useState(5)

  const handleCountChange = (count: number) => {
    if (count === 1 && reminderCount === 0) {
      postOnboardingEvent('first_reminder_created', 'reminders')
    }
    setReminderCount(count)
  }

  const quotaBadge = `${reminderCount}/${planLimit} 🔔`

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <MedicalHeader title={`Напоминания ${quotaBadge}`} showBack onBack={() => navigate('/')}> 
        <button
          type="button"
          onClick={() => navigate('/reminders/new')}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg shadow-soft hover:shadow-medium hover:bg-primary/90 transition-all duration-200"
        >
          + Добавить
        </button>
        {reminderCount === 0 && (
          <button
            type="button"
            onClick={async () => {
              await postOnboardingEvent('onboarding_completed', 'reminders', {
                skippedReminders: true,
              })
              navigate('/')
            }}
            className="ml-2 px-4 py-2 border rounded-lg text-muted-foreground hover:bg-muted transition-all duration-200"
          >
            Пропустить пока
          </button>
        )}
      </MedicalHeader>

      <main className="container mx-auto px-4 py-6">
        <RemindersList onCountChange={handleCountChange} onLimitChange={setPlanLimit} />
      </main>
    </div>
  )
}
