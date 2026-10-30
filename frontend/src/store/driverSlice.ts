import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { driverApi } from "@/api/endpoints";
import type { DriverTask, Service } from "@/types";

/** Smenasiz: bugungi jadvaldagi mashina (bo'lsa), biriktirilgan (sariq) va bajarilgan (yashil) arizalar. */
interface Today { vehicle: { id: number; plate: string; model: string | null } | null; service: Service | null }
interface DriverState { today: Today | null; tasks: DriverTask[]; done: DriverTask[]; loaded: boolean }
const initialState: DriverState = { today: null, tasks: [], done: [], loaded: false };

export const refreshDriver = createAsyncThunk("driver/refresh", async () => {
  const [today, tasks, done] = await Promise.all([driverApi.today(), driverApi.tasks(), driverApi.done()]);
  return { today, tasks, done };
});

const slice = createSlice({
  name: "driver",
  initialState,
  reducers: {
    upsertTask: (s, a: { payload: DriverTask }) => {
      const i = s.tasks.findIndex((t) => t.id === a.payload.id);
      if (i >= 0) s.tasks[i] = { ...s.tasks[i], ...a.payload };
    },
    removeTask: (s, a: { payload: number }) => { s.tasks = s.tasks.filter((t) => t.id !== a.payload); },
  },
  extraReducers: (b) => {
    b.addCase(refreshDriver.fulfilled, (s, a) => {
      s.today = a.payload.today; s.tasks = a.payload.tasks; s.done = a.payload.done; s.loaded = true;
    });
  },
});

export const { upsertTask, removeTask } = slice.actions;
export default slice.reducer;
