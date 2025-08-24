import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Routes, Route } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Suspense, lazy } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import useHardwareAcceleration from "@/hooks/use-hardware-acceleration";
import { useTelegramContext } from "@/contexts/telegram-context";
import ErrorBoundary from "@/components/ErrorBoundary";
import MedicalButton from "@/components/MedicalButton";

const Home = lazy(() => import("./pages/Home"));
const Profile = lazy(() => import("./pages/Profile"));
const Reminders = lazy(() => import("./pages/Reminders"));
const CreateReminder = lazy(() => import("./reminders/CreateReminder"));
const History = lazy(() => import("./pages/History"));
const NewMeasurement = lazy(() => import("./pages/NewMeasurement"));
const NewMeal = lazy(() => import("./pages/NewMeal"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Subscription = lazy(() => import("./pages/Subscription"));
const NotFound = lazy(() => import("./pages/NotFound"));

const queryClient = new QueryClient();

const AppContent = () => {
  const { isReady, error, tg } = useTelegramContext();
  const hasAcceleration = useHardwareAcceleration();

  const telegramBot = import.meta.env.VITE_TELEGRAM_BOT;
  const telegramLink = telegramBot
    ? `https://t.me/${telegramBot}?startapp=reminders`
    : undefined;

  const openInTelegram = (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center space-y-4">
        <p className="text-lg font-medium">
          Не удалось определить пользователя Telegram
        </p>
        <p className="text-muted-foreground">
          Попробуйте открыть приложение из Telegram.
        </p>
        {error?.code === "no-user" && telegramLink && (
          <MedicalButton asChild variant="outline">
            <a href={telegramLink} target="_blank" rel="noopener noreferrer">
              Открыть в Telegram
            </a>
          </MedicalButton>
        )}
      </div>
    </div>
  );

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

  if (!tg || error?.code === "no-user") {
    return openInTelegram;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-lg font-medium">Что-то пошло не так</p>
          <p className="text-muted-foreground">
            Попробуйте обновить приложение.
          </p>
          <p className="text-sm text-muted-foreground">
            {error.message ?? error.code}
          </p>
        </div>
      </div>
    );
  }

  return (
    <Suspense fallback={<div>Загрузка...</div>}>
      <ErrorBoundary>
        {!hasAcceleration && (
          <div className="m-4">
            <Alert variant="destructive">
              <AlertTitle>Аппаратное ускорение недоступно</AlertTitle>
              <AlertDescription>
                Графические функции могут быть отключены. В доверенной среде
                можно запустить браузер с флагом{" "}
                <code>--enable-unsafe-swiftshader</code> для программного
                рендеринга.
              </AlertDescription>
            </Alert>
          </div>
        )}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/reminders" element={<Reminders />} />
          <Route path="/reminders/new" element={<CreateReminder />} />
          <Route path="/reminders/:id/edit" element={<CreateReminder />} />
          <Route path="/history" element={<History />} />
          <Route path="/history/new-measurement" element={<NewMeasurement />} />
          <Route path="/history/new-meal" element={<NewMeal />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/subscription" element={<Subscription />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ErrorBoundary>
    </Suspense>
  );
};

const App = () => (
  <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <AppContent />
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
