
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useTelegram } from "@/hooks/useTelegram";
import { ThemeProvider } from "next-themes";
import Home from "./pages/Home";
import Profile from "./pages/Profile";
import Reminders from "./pages/Reminders";
import History from "./pages/History";
import NewMeasurement from "./pages/NewMeasurement";
import NewMeal from "./pages/NewMeal";
import Analytics from "./pages/Analytics";
import Subscription from "./pages/Subscription";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const AppContent = () => {
  const { isReady } = useTelegram();

  if (!isReady) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-center">
          <div className="w-16 h-16 rounded-full bg-primary/20 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Загрузка СахарФото...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/reminders" element={<Reminders />} />
      <Route path="/history" element={<History />} />
      <Route path="/history/new-measurement" element={<NewMeasurement />} />
      <Route path="/history/new-meal" element={<NewMeal />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/subscription" element={<Subscription />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

const App = () => (
  <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter basename="/ui">
          <AppContent />
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
