import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis } from 'recharts';
import { MedicalHeader } from '@/components/MedicalHeader';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';

const data = [
  { date: '2024-01-01', sugar: 5.5 },
  { date: '2024-01-02', sugar: 6.1 },
  { date: '2024-01-03', sugar: 5.8 },
  { date: '2024-01-04', sugar: 6.0 },
  { date: '2024-01-05', sugar: 5.4 },
];

const Analytics = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <MedicalHeader title="Аналитика" showBack onBack={() => navigate('/history')} />
      <main className="container mx-auto px-4 py-6">
        <ChartContainer
          config={{
            sugar: {
              label: 'Сахар',
              color: 'hsl(var(--chart-1))',
            },
          }}
          className="h-64"
        >
          <LineChart data={data}>
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
