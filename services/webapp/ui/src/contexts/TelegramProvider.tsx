import { ReactNode } from "react";
import { useTelegram } from "@/hooks/useTelegram";
import { TelegramContext } from "./telegram-context";

export const TelegramProvider = ({ children }: { children: ReactNode }) => {
  const telegram = useTelegram();
  return (
    <TelegramContext.Provider value={telegram}>
      {children}
    </TelegramContext.Provider>
  );
};

