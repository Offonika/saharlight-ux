import { toast as showToast } from "@/components/ui/use-toast";

export function useToast() {
  const success = (description: string, title = "Готово") =>
    showToast({ title, description });

  const error = (description: string, title = "Ошибка") =>
    showToast({ title, description, variant: "destructive" });

  return { success, error };
}

export type ToastHook = ReturnType<typeof useToast>;
