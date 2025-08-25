import RemindersList from '../features/reminders/pages/RemindersList'
import { MedicalHeader } from '@/components/MedicalHeader'
import { useNavigate } from 'react-router-dom'

export default function Reminders() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader title="Напоминания" showBack onBack={() => navigate('/')}>
        <a 
          href="/reminders/new" 
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          + Добавить
        </a>
      </MedicalHeader>

      <main className="container mx-auto px-4 py-6">
        <RemindersList />
      </main>
    </div>
  )
}
