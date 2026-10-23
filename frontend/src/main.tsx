import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { Provider } from "react-redux";
import { App } from "./App";
import { I18nProvider } from "./i18n/I18nContext";
import { store } from "./store";
import { theme } from "./theme";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <ThemeProvider theme={theme} defaultMode="system">
        <CssBaseline />
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeProvider>
    </Provider>
  </StrictMode>,
);
