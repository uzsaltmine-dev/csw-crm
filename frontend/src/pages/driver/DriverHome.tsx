import { useState } from "react";
import { Alert, Button, Card, CardActionArea, CardContent, Chip, Stack, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useI18n } from "@/i18n/I18nContext";
import { useAppDispatch, useAppSelector } from "@/store";
import { refreshDriver } from "@/store/driverSlice";
import { ShiftEndDialog } from "./ShiftEndDialog";
import { ShiftStart } from "./ShiftStart";

export function DriverHome() {
  const { t } = useI18n();
  const nav = useNavigate();
  const dispatch = useAppDispatch();
  const { shift, tasks, loaded } = useAppSelector((s) => s.driver);
  const [ending, setEnding] = useState(false);

  if (!loaded) return <Typography>{t("loading")}</Typography>;

  if (!shift) {
    return (
      <Alert severity="info" action={<Button onClick={() => dispatch(refreshDriver())}>{t("refresh")}</Button>}>
        <b>{t("no_shift_title")}.</b> {t("no_shift_text")}
      </Alert>
    );
  }
  if (shift.status === "opened") return <ShiftStart shift={shift} />;

  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="h6">{t("my_tasks")}</Typography>
        <Button variant="outlined" onClick={() => setEnding(true)}>{t("end_shift")}</Button>
      </Stack>
      {tasks.length === 0 && <Alert severity="info">{t("no_tasks")}</Alert>}
      {tasks.map((task) => (
        <Card key={task.id} variant="outlined">
          <CardActionArea onClick={() => nav(`/driver/requests/${task.id}`)}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" spacing={1}>
                <Typography fontWeight={600}>{task.customer.name}</Typography>
                <Chip size="small" color="primary" variant="outlined" label={t(`s_${task.status}` as "s_assigned")} />
              </Stack>
              <Typography variant="body2" color="text.secondary">{task.customer.address}</Typography>
              <Typography variant="body2" sx={{ fontFamily: "monospace" }}>{task.naryad_no} · {task.number}</Typography>
            </CardContent>
          </CardActionArea>
        </Card>
      ))}
      <ShiftEndDialog shift={shift} open={ending} onClose={() => setEnding(false)} />
    </Stack>
  );
}
