import React, { createContext, useContext, useState } from "react";

type T = { success: (m: string) => void, error: (m: string) => void };
const C = createContext<T>({ success: () => {}, error: () => {} });

export const useToast = () => useContext(C);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [msg, set] = useState<{ t: "ok" | "err"; m: string } | null>(null);
  
  const api = {
    success: (m: string) => {
      set({ t: "ok", m });
      setTimeout(() => set(null), 2000);
    },
    error: (m: string) => {
      set({ t: "err", m });
      setTimeout(() => set(null), 3000);
    }
  };
  
  return (
    <C.Provider value={api}>
      {children}
      {msg && (
        <div 
          className={`fixed bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-xl text-white z-50 animate-slide-up ${
            msg.t === "ok" ? "bg-green-600" : "bg-red-600"
          }`}
        >
          {msg.m}
        </div>
      )}
    </C.Provider>
  );
}