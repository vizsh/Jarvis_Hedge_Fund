import { create } from "zustand";

/** Cross-page UI flags that are not about the portfolio itself. */
export const useUI = create<{ builder: boolean; setBuilder: (v: boolean) => void }>((set) => ({
  builder: false,
  setBuilder: (builder) => set({ builder }),
}));
