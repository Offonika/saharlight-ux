import { Clock, User, BookOpen, Star } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { MedicalHeader } from '@/components/MedicalHeader';
import { useTelegram } from '@/hooks/useTelegram';

const menuItems = [
  {
    id: 'reminders',
    title: 'Напоминания',
    icon: Clock,
    description: 'AI-уведомления',
    route: '/reminders',
    gradient: 'bg-gradient-to-br from-tech-primary to-tech-accent'
  },
  {
    id: 'profile', 
    title: 'Мой профиль',
    icon: User,
    description: 'Умные настройки',
    route: '/profile',
    gradient: 'bg-gradient-to-br from-tech-secondary to-tech-primary'
  },
  {
    id: 'history',
    title: 'История',
    icon: BookOpen,
    description: 'Аналитика данных',
    route: '/history',
    gradient: 'bg-gradient-to-br from-tech-accent to-tech-secondary'
  },
  {
    id: 'subscription',
    title: 'Подписка',
    icon: Star,
    description: 'PRO возможности',
    route: '/subscription',
    gradient: 'bg-gradient-to-br from-warning to-tech-warning'
  }
];

const Home = () => {
  const navigate = useNavigate();
  const { user } = useTelegram();

  const handleTileClick = (route: string) => {
    navigate(route);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <MedicalHeader title="СахарФото" />
      
      <main className="container mx-auto px-4 py-6">
        {/* Приветствие */}
        <div className="mb-8 animate-slide-up">
          <h2 className="text-2xl font-bold text-foreground mb-2">
            Добро пожаловать{user?.first_name ? `, ${user.first_name}` : ''}!
          </h2>
          <p className="text-muted-foreground">
            Ваш персональный ассистент для управления диабетом
          </p>
        </div>

        {/* Главное меню */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          {menuItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <div
                key={item.id}
                className="tech-tile"
                style={{ animationDelay: `${index * 100}ms` }}
                onClick={() => handleTileClick(item.route)}
              >
                <div className={`w-14 h-14 rounded-lg flex items-center justify-center mb-3 ${item.gradient} relative`}>
                  <Icon className="w-7 h-7 text-white drop-shadow-lg" />
                  <div className="absolute inset-0 rounded-lg bg-gradient-to-t from-black/20 to-transparent"></div>
                </div>
                <h3 className="font-semibold text-foreground mb-1">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </div>
            );
          })}
        </div>

        {/* Быстрые действия */}
        <div className="tech-card animate-fade-in" style={{ animationDelay: '400ms' }}>
          <h3 className="font-semibold text-foreground mb-4 neon-text">Быстрые действия</h3>
          <div className="grid grid-cols-2 gap-3">
            <button className="tech-button-secondary py-3 text-sm font-medium">
              📊 Записать сахар
            </button>
            <button className="tech-button-secondary py-3 text-sm font-medium">
              🍽️ Добавить еду
            </button>
          </div>
        </div>

        {/* Статистика дня */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          <div className="tech-card text-center py-5 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-tech-primary/20 to-transparent"></div>
            <div className="relative z-10">
              <div className="text-3xl font-bold text-tech-primary glow-effect">6.2</div>
              <div className="text-xs text-muted-foreground mt-1">ммоль/л</div>
            </div>
          </div>
          <div className="tech-card text-center py-5 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-tech-accent/20 to-transparent"></div>
            <div className="relative z-10">
              <div className="text-3xl font-bold text-tech-accent glow-effect">4</div>
              <div className="text-xs text-muted-foreground mt-1">ХЕ</div>
            </div>
          </div>
          <div className="tech-card text-center py-5 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-tech-success/20 to-transparent"></div>
            <div className="relative z-10">
              <div className="text-3xl font-bold text-tech-success glow-effect">12</div>
              <div className="text-xs text-muted-foreground mt-1">ед.</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home;