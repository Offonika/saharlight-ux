import { Star, Clock, User, Bell, LineChart } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MedicalHeader } from '@/components/MedicalHeader';
import { useTelegram } from '@/hooks/useTelegram';
import MedicalButton from '@/components/MedicalButton';
import { StatCard } from '@/components/StatCard';
import { fetchDayStats } from '@/api/stats';

const menuItems = [
  {
    id: 'history',
    title: 'История',
    icon: Clock,
    description: 'Журнал измерений',
    route: '/history',
    color: 'medical-blue',
  },
  {
    id: 'profile',
    title: 'Профиль',
    icon: User,
    description: 'Ваши настройки',
    route: '/profile',
    color: 'medical-teal',
  },
  {
    id: 'reminders',
    title: 'Напоминания',
    icon: Bell,
    description: 'Управление напоминаниями',
    route: '/reminders',
    color: 'medical-success',
  },
  {
    id: 'analytics',
    title: 'Аналитика',
    icon: LineChart,
    description: 'Статистика и отчёты',
    route: '/analytics',
    color: 'medical-warning',
  },
  {
    id: 'subscription',
    title: 'Подписка',
    icon: Star,
    description: 'Тарифы и оплата',
    route: '/subscription',
    color: 'medical-warning',
  },
];

const Home = () => {
  const navigate = useNavigate();
  const { user } = useTelegram();

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['day-stats', user?.id],
    queryFn: () => fetchDayStats(user?.id ?? 0),
    enabled: !!user?.id,
  });

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
        <div
          className={`grid gap-4 mb-8 ${
            menuItems.length === 1 ? 'grid-cols-1 justify-items-center' : 'grid-cols-2'
          }`}
        >
          {menuItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <div
                key={item.id}
                className="medical-tile"
                style={{ animationDelay: `${index * 100}ms` }}
                onClick={() => handleTileClick(item.route)}
              >
               <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 transition-all duration-300 ${
                 item.color === 'medical-blue' ? 'bg-medical-blue/10 shadow-glow' :
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
            <MedicalButton
              variant="secondary"
              size="lg"
              className="py-2 text-sm"
              onClick={() => navigate('/history/new-measurement')}
            >
              Записать сахар
            </MedicalButton>
            <MedicalButton
              variant="secondary"
              size="lg"
              className="py-2 text-sm"
              onClick={() => navigate('/history/new-meal')}
            >
              Добавить еду
            </MedicalButton>
          </div>
        </div>

        {/* Статистика дня */}
        {isLoading && (
          <p className="text-center text-muted-foreground mt-6">Загрузка статистики...</p>
        )}
        {error && (
          <p className="text-center text-destructive mt-6">
            Не удалось загрузить статистику
          </p>
        )}
        <div className="mt-6 grid grid-cols-3 gap-3">
          <StatCard
            value={stats?.sugar ?? 0}
            unit="ммоль/л"
            label="Сахар"
            variant="sugar"
          />
          <StatCard
            value={stats?.breadUnits ?? 0}
            unit="ХЕ"
            label="Хлебные единицы"
            variant="bread"
          />
          <StatCard
            value={stats?.insulin ?? 0}
            unit="ед."
            label="Инсулин"
            variant="insulin"
          />
        </div>
      </main>
    </div>
  );
};

export default Home;
