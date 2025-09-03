/// file: src/App.tsx
import React from "react"
import { Toaster } from "@/components/ui/toaster"
import { Toaster as Sonner } from "@/components/ui/sonner"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import { useTelegram } from "@/hooks/useTelegram"
import { ThemeProvider } from "next-themes"
import { ToastProvider } from "./shared/toast"

import Home from "./pages/Home"
import Profile from "./pages/Profile"
import Reminders from "./pages/Reminders"
import RemindersCreate from "./features/reminders/pages/RemindersCreate"
import RemindersEdit from "./features/reminders/pages/RemindersEdit"
import History from "./pages/History"
import NewMeasurement from "./pages/NewMeasurement"
import NewMeal from "./pages/NewMeal"
import Analytics from "./pages/Analytics"
import Subscription from "./pages/Subscription"
import NotFound from "./pages/NotFound"
import PaywallGuard from "./features/paywall/PaywallGuard"

const queryClient = new QueryClient()

const AppContent = () => {
  const { isReady } = useTelegram()

  if (!isReady) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-center">
          <div className="w-16 h-16 rounded-full bg-primary/20 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Загрузка СахарФото...</p>
        </div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/reminders" element={<PaywallGuard><Reminders /></PaywallGuard>} />
      <Route path="/reminders/new" element={<PaywallGuard><RemindersCreate /></PaywallGuard>} />
      <Route path="/reminders/:id/edit" element={<PaywallGuard><RemindersEdit /></PaywallGuard>} />
      <Route path="/history" element={<History />} />
      <Route path="/history/new-measurement" element={<NewMeasurement />} />
      <Route path="/history/new-meal" element={<NewMeal />} />
      <Route path="/analytics" element={<PaywallGuard><Analytics /></PaywallGuard>} />
      <Route path="/subscription" element={<Subscription />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

const baseName = import.meta.env.BASE_URL.replace(/\/$/, "") || "/"

const App = () => (
  <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter basename={baseName}>
          <AppContent />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  </ThemeProvider>
)

export default App
