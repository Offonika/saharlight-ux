import { Info } from "lucide-react";
import { HoverCard, HoverCardTrigger, HoverCardContent } from "@/components/ui/hover-card";

interface HelpHintProps {
  text: string;
}

const HelpHint = ({ text }: HelpHintProps) => (
  <HoverCard>
    <HoverCardTrigger asChild>
      <button
        type="button"
        className="ml-1 text-muted-foreground hover:text-foreground focus:outline-none"
        aria-label="Справка"
      >
        <Info className="w-4 h-4" />
      </button>
    </HoverCardTrigger>
    <HoverCardContent className="max-w-xs">{text}</HoverCardContent>
  </HoverCard>
);

export default HelpHint;
