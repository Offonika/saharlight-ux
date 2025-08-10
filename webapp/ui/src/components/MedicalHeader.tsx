import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MedicalHeaderProps {
  title: string;
  showBack?: boolean;
  onBack?: () => void;
  children?: React.ReactNode;
}

export const MedicalHeader = ({ title, showBack, onBack, children }: MedicalHeaderProps) => {
  return (
    <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {showBack && (
              <Button
                onClick={onBack}
                variant="ghost"
                size="icon"
                aria-label="Назад"
              >
                <ArrowLeft className="w-5 h-5" />
              </Button>
            )}
            <h1 className="text-xl font-semibold text-foreground">{title}</h1>
          </div>
          {children}
        </div>
      </div>
    </header>
  );
};
