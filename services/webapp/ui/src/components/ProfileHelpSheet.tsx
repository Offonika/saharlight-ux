import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

interface ProfileHelpSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const ProfileHelpSheet = ({ open, onOpenChange }: ProfileHelpSheetProps) => (
  <Sheet open={open} onOpenChange={onOpenChange}>
    <SheetContent side="bottom" className="space-y-4">
      <SheetHeader>
        <SheetTitle>Справка по профилю</SheetTitle>
      </SheetHeader>
      <div className="space-y-3 text-sm text-muted-foreground">
        <p>
          <strong className="text-foreground">ICR</strong> — сколько граммов
          углеводов покрывает 1 единица быстрого инсулина.
        </p>
        <p>
          <strong className="text-foreground">КЧ</strong> — на сколько ммоль/л
          снижает уровень глюкозы 1 единица быстрого инсулина.
        </p>
        <p>
          Эти параметры индивидуальны и должны быть определены совместно с вашим
          врачом.
        </p>
      </div>
    </SheetContent>
  </Sheet>
);

export default ProfileHelpSheet;
