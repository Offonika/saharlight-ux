import type { LucideIcon } from 'lucide-react';
import { Clock, User, BookOpen, Star } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MedicalHeader } from '@/components/MedicalHeader';
import MedicalButton from '@/components/MedicalButton';
import { useTelegramContext } from '@/contexts/telegram-context';
import { fetchDayStats, fallbackDayStats } from '@/api/stats';

const COLOR_MAP = {
  'medical-blue': {
    bg: 'bg-medical-blue/10',
    text: 'text-medical-blue',
  },
  'medical-teal': {
    bg: 'bg-medical-teal/10',
    text: 'text-medical-teal',
  },
  'medical-success': {
    bg: 'bg-medical-success/10',
    text: 'text-medical-success',
  },
  'medical-warning': {
    bg: 'bg-medical-warning/10',
    text: 'text-medical-warning',
  },
} as const;

interface MenuItem {
  id: string;
  title: string;
  icon: LucideIcon;
  description: string;
  route: string;
  color: keyof typeof COLOR_MAP;
}

const menuItems: MenuItem[] = [
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

const Home = (): JSX.Element => {
  const navigate = useNavigate();
  const { user } = useTelegramContext();

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['day-stats', user?.id],
    queryFn: () => fetchDayStats(user?.id ?? 0),
    enabled: !!user?.id,
    placeholderData: fallbackDayStats,
  });

  const dayStats = stats ?? fallbackDayStats;

  const handleTileClick = (route: string): void => {
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
            const { bg, text } = COLOR_MAP[item.color];
            return (
              <div
                key={item.id}
                className="medical-tile"
                style={{ animationDelay: `${index * 100}ms` }}
                onClick={() => handleTileClick(item.route)}
              >
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${bg}`}
                >
                  <Icon className={`w-6 h-6 ${text}`} />
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
          <div className="medical-card text-center py-4">
            <div className="text-2xl font-bold text-medical-blue">{dayStats.sugar}</div>
            <div className="text-xs text-muted-foreground">ммоль/л</div>
          </div>
          <div className="medical-card text-center py-4">
            <div className="text-2xl font-bold text-medical-teal">{dayStats.breadUnits}</div>
            <div className="text-xs text-muted-foreground">ХЕ</div>
          </div>
          <div className="medical-card text-center py-4">
            <div className="text-2xl font-bold text-medical-success">{dayStats.insulin}</div>
            <div className="text-xs text-muted-foreground">ед.</div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home;
