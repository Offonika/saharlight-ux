import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { MedicalHeader } from '@/components/MedicalHeader';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { fetchAnalytics, fallbackAnalytics } from '@/api/stats';
import { useTelegramContext } from '@/contexts/telegram-context';

const Analytics = () => {
  const navigate = useNavigate();
  const { user } = useTelegramContext();

  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', user?.id],
    queryFn: () => fetchAnalytics(user?.id ?? 0),
    enabled: !!user?.id,
    placeholderData: fallbackAnalytics,
  });

  const chartData = data ?? fallbackAnalytics;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
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
      </main>
    </div>
  );
};

export default Analytics;
