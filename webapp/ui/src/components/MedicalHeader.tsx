import { ArrowLeft } from 'lucide-react';

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
              <button
                onClick={onBack}
                className="p-2 rounded-lg hover:bg-secondary/80 active:scale-95 transition-all duration-200"
                aria-label="Назад"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
            )}
            <h1 className="text-xl font-semibold text-foreground">{title}</h1>
          </div>
          {children}
        </div>
      </div>
    </header>
  );
};