import { useNavigate } from 'react-router-dom';
import { Check, Star, Users, Zap } from 'lucide-react';
import { MedicalHeader } from '@/components/MedicalHeader';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';

interface TariffPlan {
  id: string;
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  recommended?: boolean;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  color: string;
}

const tariffPlans: TariffPlan[] = [
  {
    id: 'free',
    name: 'Free',
    price: '0',
    period: 'навсегда',
    description: 'Базовые функции для начинающих',
    features: [
      'Дневник питания',
      'Базовые напоминания',
      'История записей (30 дней)',
      'Простая аналитика'
    ],
    icon: Zap,
    color: 'neutral-500'
  },
  {
    id: 'pro',
    name: 'PRO',
    price: '299',
    period: 'в месяц',
    description: 'Полный функционал с GPT-аналитикой',
    features: [
      'Все функции Free',
      'GPT-анализ питания',
      'Расчет доз инсулина',
      'Неограниченная история',
      'Экспорт данных',
      'Подробная аналитика',
      'Приоритетная поддержка'
    ],
    recommended: true,
    icon: Star,
    color: 'medical-blue'
  },
  {
    id: 'family',
    name: 'Family',
    price: '499',
    period: 'в месяц',
    description: 'Для всей семьи до 4 человек',
    features: [
      'Все функции PRO',
      'До 4 учетных записей',
      'Общая статистика семьи',
      'Семейные напоминания',
      'Консультации эндокринолога',
      'Персональные рекомендации'
    ],
    icon: Users,
    color: 'medical-teal'
  }
];

const Subscription = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubscribe = (planId: string) => {
    toast({
      title: "Подписка оформлена",
      description: `Тариф ${tariffPlans.find(p => p.id === planId)?.name} успешно активирован`
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader 
        title="Подписка и тарифы" 
        showBack 
        onBack={() => navigate('/')}
      />
      
      <main className="container mx-auto px-4 py-6">
        {/* Описание */}
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-foreground mb-3">
            Выберите подходящий тариф
          </h2>
          <p className="text-muted-foreground">
            Расширьте возможности СахарФото для лучшего контроля диабета
          </p>
        </div>

        {/* Тарифные планы */}
        <div className="space-y-4 mb-8">
          {tariffPlans.map((plan, index) => {
            const Icon = plan.icon;
            return (
              <div
                key={plan.id}
                className={`medical-card ${plan.recommended ? 'ring-2 ring-primary/50' : ''} animate-slide-up`}
                style={{ animationDelay: `${index * 150}ms` }}
              >
                {plan.recommended && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <span className="bg-primary text-primary-foreground px-3 py-1 rounded-full text-sm font-medium">
                      Рекомендуем
                    </span>
                  </div>
                )}
                
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    plan.color === 'neutral-500' ? 'bg-neutral-500/10' :
                    plan.color === 'medical-blue' ? 'bg-medical-blue/10' :
                    'bg-medical-teal/10'
                  }`}>
                    <Icon className={`w-6 h-6 ${
                      plan.color === 'neutral-500' ? 'text-neutral-500' :
                      plan.color === 'medical-blue' ? 'text-medical-blue' :
                      'text-medical-teal'
                    }`} />
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xl font-bold text-foreground">{plan.name}</h3>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-primary">
                          {plan.price === '0' ? 'Бесплатно' : `${plan.price} ₽`}
                        </div>
                        <div className="text-sm text-muted-foreground">{plan.period}</div>
                      </div>
                    </div>
                    
                    <p className="text-muted-foreground mb-4">{plan.description}</p>
                    
                    <div className="space-y-2 mb-6">
                      {plan.features.map((feature, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-success flex-shrink-0" />
                          <span className="text-sm text-foreground">{feature}</span>
                        </div>
                      ))}
                    </div>
                    
                    <Button
                      onClick={() => handleSubscribe(plan.id)}
                      disabled={plan.price === '0'}
                      className="w-full"
                      size="lg"
                      variant={plan.recommended ? 'default' : 'secondary'}
                    >
                      {plan.price === '0' ? 'Текущий тариф' : 'Выбрать тариф'}
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Информация об оплате */}
        <div className="medical-card">
          <h3 className="font-semibold text-foreground mb-4">Информация об оплате</h3>
          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-success" />
              <span>Безопасная оплата через Telegram Payments</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-success" />
              <span>Отмена подписки в любое время</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-success" />
              <span>7 дней бесплатного использования PRO</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-success" />
              <span>Техническая поддержка 24/7</span>
            </div>
          </div>
        </div>

        {/* Часто задаваемые вопросы */}
        <div className="mt-8 medical-card">
          <h3 className="font-semibold text-foreground mb-4">Часто задаваемые вопросы</h3>
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-foreground mb-1">
                Можно ли отменить подписку?
              </h4>
              <p className="text-sm text-muted-foreground">
                Да, вы можете отменить подписку в любое время. Доступ к функциям сохраняется до окончания оплаченного периода.
              </p>
            </div>
            
            <div>
              <h4 className="font-medium text-foreground mb-1">
                Что такое GPT-анализ питания?
              </h4>
              <p className="text-sm text-muted-foreground">
                Искусственный интеллект анализирует ваши фотографии еды и автоматически рассчитывает углеводы, калории и рекомендуемую дозу инсулина.
              </p>
            </div>
            
            <div>
              <h4 className="font-medium text-foreground mb-1">
                Безопасны ли мои данные?
              </h4>
              <p className="text-sm text-muted-foreground">
                Все данные шифруются и хранятся в соответствии с требованиями GDPR. Мы не передаем информацию третьим лицам.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Subscription;