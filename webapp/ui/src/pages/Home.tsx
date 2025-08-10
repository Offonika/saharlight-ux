import { Clock, User, BookOpen, Star } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { MedicalHeader } from '@/components/MedicalHeader';
import { useTelegram } from '@/hooks/useTelegram';

const menuItems = [
  {
    id: 'reminders',
    title: 'Напоминания',
    icon: Clock,
    description: 'Настройка уведомлений',
    route: '/reminders',
    color: 'medical-blue'
  },
  {
    id: 'profile', 
    title: 'Мой профиль',
    icon: User,
    description: 'Личные настройки',
    route: '/profile',
    color: 'medical-teal'
  },
  {
    id: 'history',
    title: 'История',
    icon: BookOpen,
    description: 'Записи о сахаре',
    route: '/history',
    color: 'medical-success'
  },
  {
    id: 'subscription',
    title: 'Подписка',
    icon: Star,
    description: 'Тарифы и оплата',
    route: '/subscription',
    color: 'medical-warning'
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
                className="medical-tile"
                style={{ animationDelay: `${index * 100}ms` }}
                onClick={() => handleTileClick(item.route)}
              >
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${
                item.color === 'medical-blue' ? 'bg-medical-blue/10' :
                item.color === 'medical-teal' ? 'bg-medical-teal/10' :
                item.color === 'medical-success' ? 'bg-medical-success/10' :
                'bg-medical-warning/10'
              }`}>
                <Icon className={`w-6 h-6 ${
                  item.color === 'medical-blue' ? 'text-medical-blue' :
                  item.color === 'medical-teal' ? 'text-medical-teal' :
                  item.color === 'medical-success' ? 'text-medical-success' :
                  'text-medical-warning'
                }`} />
                </div>
                <h3 className="font-semibold text-foreground mb-1">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </div>
            );
          })}
        </div>

        {/* Быстрые действия */}
        <div className="medical-card animate-fade-in" style={{ animationDelay: '400ms' }}>
          <h3 className="font-semibold text-foreground mb-4">Быстрые действия</h3>
          <div className="grid grid-cols-2 gap-3">
            <button
              className="medical-button-secondary py-2 text-sm"
              onClick={() => navigate('/history/new-measurement')}
            >
              Записать сахар
            </button>
            <button
              className="medical-button-secondary py-2 text-sm"
              onClick={() => navigate('/history/new-meal')}
            >
              Добавить еду
            </button>
          </div>
        </div>

        {/* Статистика дня */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          <div className="medical-card text-center py-4">
            <div className="text-2xl font-bold text-medical-blue">6.2</div>
            <div className="text-xs text-muted-foreground">ммоль/л</div>
          </div>
          <div className="medical-card text-center py-4">
            <div className="text-2xl font-bold text-medical-teal">4</div>
            <div className="text-xs text-muted-foreground">ХЕ</div>
          </div>
          <div className="medical-card text-center py-4">
            <div className="text-2xl font-bold text-medical-success">12</div>
            <div className="text-xs text-muted-foreground">ед.</div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home;