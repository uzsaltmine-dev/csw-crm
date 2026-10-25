import { useState } from "react";
import { IconButton, InputAdornment, TextField, type TextFieldProps } from "@mui/material";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import { useI18n } from "@/i18n/I18nContext";

/** Parol maydoni: ko'z belgisini bosib kiritilgan parolni ko'rish/yashirish. */
export function PasswordField({ defaultVisible = false, ...props }: TextFieldProps & { defaultVisible?: boolean }) {
  const { t } = useI18n();
  const [show, setShow] = useState(defaultVisible);
  return (
    <TextField {...props} type={show ? "text" : "password"}
      slotProps={{ input: { endAdornment: (
        <InputAdornment position="end">
          <IconButton aria-label={t(show ? "hide_password" : "show_password")} title={t(show ? "hide_password" : "show_password")}
            onClick={() => setShow((v) => !v)} onMouseDown={(e) => e.preventDefault()} edge="end" tabIndex={-1}>
            {show ? <VisibilityOff /> : <Visibility />}
          </IconButton>
        </InputAdornment>
      ) } }} />
  );
}
