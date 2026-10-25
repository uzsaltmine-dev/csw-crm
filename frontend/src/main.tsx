import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { Provider } from "react-redux";
import { Toaster } from "sonner";
import { App } from "./App";
import { I18nProvider } from "./i18n/I18nContext";
import { store } from "./store";
import { theme } from "./theme";
import { DialogHost } from "./lib/dialogs";
import { detectSessionMode } from "./lib/session";

// Sessiya rejimini (cookie yoki tab) bilib olib, keyin ilovani chizamiz
detectSessionMode().finally(() => createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <ThemeProvider theme={theme} defaultMode="system">
        <CssBaseline />
        <I18nProvider>
          <App />
          <DialogHost />
          {/* shadcn/ui toastlari (Sonner): navbar ostida, o'ngda, ustma-ust taxlanadi */}
          <Toaster position="top-right" offset={76} gap={8} visibleToasts={5} closeButton theme="system"
            toastOptions={{ style: { fontFamily: '"Golos Text", "Segoe UI", system-ui, sans-serif', fontSize: 14, borderRadius: 10 } }} />
        </I18nProvider>
      </ThemeProvider>
    </Provider>
  </StrictMode>,
));
