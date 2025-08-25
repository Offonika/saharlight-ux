import RemindersList from '../features/reminders/pages/RemindersList'
import { MedicalHeader } from '@/components/MedicalHeader'
import { useNavigate } from 'react-router-dom'

export default function Reminders() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <MedicalHeader title="Напоминания" showBack onBack={() => navigate('/')}>
        <a 
          href="/reminders/new" 
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg shadow-soft hover:shadow-medium hover:bg-primary/90 transition-all duration-200"
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
