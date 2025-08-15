import { createContext, useContext, ReactNode } from "react";
import { useTelegram } from "@/hooks/useTelegram";

// TelegramContext will hold values returned by useTelegram hook
const TelegramContext = createContext<ReturnType<typeof useTelegram> | null>(null);

export const TelegramProvider = ({ children }: { children: ReactNode }) => {
  const telegram = useTelegram();
  return (
    <TelegramContext.Provider value={telegram}>
      {children}
    </TelegramContext.Provider>
  );
};

export const useTelegramContext = () => {
  const context = useContext(TelegramContext);
  if (!context) {
    throw new Error("useTelegramContext must be used within TelegramProvider");
  }
  return context;
};

