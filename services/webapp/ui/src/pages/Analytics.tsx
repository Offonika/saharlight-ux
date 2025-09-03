import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { MedicalHeader } from '@/components/MedicalHeader';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { useTelegram } from '@/hooks/useTelegram';
import { fetchAnalytics } from '@/api/stats';

const Analytics = () => {
  const navigate = useNavigate();
  const { user } = useTelegram();

  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', user?.id],
    queryFn: () => fetchAnalytics(user?.id ?? 0),
    enabled: !!user?.id,
  });

  const chartData = data ?? [];

  return (
    <div className="min-h-screen bg-background">
      <MedicalHeader title="Аналитика" showBack onBack={() => navigate('/history')} />
      <main className="container mx-auto px-4 py-6">
        {isLoading && (
          <p className="text-center text-muted-foreground mb-4">Загрузка...</p>
        )}
        {error && (
          <p className="text-center text-destructive mb-4">
            Не удалось загрузить данные
          </p>
        )}
        
        <div className="medical-card bg-gradient-medical/5 border-medical-blue/20">
          <h3 className="font-semibold text-foreground mb-4">График сахара</h3>
          <ChartContainer
            config={{
              sugar: {
                label: 'Сахар',
                color: 'hsl(var(--chart-1))',
              },
            }}
            className="h-64"
          >
            <LineChart data={chartData}>
              <XAxis dataKey="date" />
              <YAxis />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line
                type="monotone"
                dataKey="sugar"
                stroke="var(--color-sugar)"
                strokeWidth={2}
                dot
              />
            </LineChart>
          </ChartContainer>
        </div>
        
        {/* Статистические карточки */}
        <div className="grid grid-cols-2 gap-3 mt-6">
          <div className="medical-card text-center bg-gradient-success/5 border-medical-success/20">
            <div className="text-2xl font-bold text-medical-success">6.8</div>
            <div className="text-xs text-muted-foreground">Средний сахар</div>
          </div>
          <div className="medical-card text-center bg-gradient-warning/5 border-medical-warning/20">
            <div className="text-2xl font-bold text-medical-warning">89%</div>
            <div className="text-xs text-muted-foreground">Время в цели</div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Analytics;
