import { createTheme } from "@mui/material/styles";

// Demo bilan bir xil palitra: yashil asosiy rang, ko'kish-yashil neytrallar
export const theme = createTheme({
  cssVariables: true,
  colorSchemes: {
    light: { palette: { primary: { main: "#1d6b4f" }, background: { default: "#f3f5f2", paper: "#ffffff" } } },
    dark: { palette: { primary: { main: "#4fbf8c" }, background: { default: "#121714", paper: "#1a211d" } } },
  },
  shape: { borderRadius: 10 },
  typography: { fontFamily: '"Golos Text", "Segoe UI", system-ui, sans-serif', button: { textTransform: "none", fontWeight: 600 } },
  components: {
    MuiButton: { styleOverrides: { sizeLarge: { minHeight: 52, paddingInline: 24 } } }, // planshetda qo'lqop bilan bosish uchun
  },
});
