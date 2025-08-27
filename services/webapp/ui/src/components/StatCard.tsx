import { cn } from '@/lib/utils';

interface StatCardProps {
  value: string | number;
  unit: string;
  label?: string;
  variant?: 'sugar' | 'bread' | 'insulin' | 'default';
  className?: string;
}

const variantStyles = {
  sugar: 'text-medical-blue bg-medical-blue/5 border-medical-blue/20',
  bread: 'text-medical-teal bg-medical-teal/5 border-medical-teal/20', 
  insulin: 'text-medical-success bg-medical-success/5 border-medical-success/20',
  default: 'text-foreground bg-background border-border'
};

export const StatCard = ({ 
  value, 
  unit, 
  label, 
  variant = 'default', 
  className 
}: StatCardProps) => {
  return (
    <div className={cn(
      'medical-card text-center py-4 border-2 transition-all duration-300 hover:scale-[1.02]',
      variantStyles[variant],
      className
    )}>
      <div className="text-2xl font-bold mb-1">{value}</div>
      <div className="text-xs opacity-75 font-medium">{unit}</div>
      {label && (
        <div className="text-xs opacity-60 mt-1">{label}</div>
      )}
    </div>
  );
};