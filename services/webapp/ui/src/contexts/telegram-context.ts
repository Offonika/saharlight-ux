import { createContext, useContext } from "react"
import type { useTelegram } from "@/hooks/useTelegram"

const TelegramContext = createContext<ReturnType<typeof useTelegram> | null>(null)

const useTelegramContext = () => {
  const context = useContext(TelegramContext)
  if (!context) {
    throw new Error("useTelegramContext must be used within TelegramProvider")
  }
  return context
}

export { TelegramContext, useTelegramContext }
