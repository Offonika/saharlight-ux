import { createContext, useContext } from "react"
import { useTelegram } from "@/hooks/useTelegram"

type TelegramHook = ReturnType<typeof useTelegram>

const TelegramContext = createContext<TelegramHook | null>(null)

const useTelegramContext = () => {
  const context = useContext(TelegramContext)
  if (!context) {
    throw new Error("useTelegramContext must be used within TelegramProvider")
  }
  return context
}

export { TelegramContext, useTelegramContext }
