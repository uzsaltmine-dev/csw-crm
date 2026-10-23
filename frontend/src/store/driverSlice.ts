import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { driverApi } from "@/api/endpoints";
import type { DriverTask, Shift } from "@/types";

interface DriverState { shift: Shift | null; tasks: DriverTask[]; loaded: boolean }
const initialState: DriverState = { shift: null, tasks: [], loaded: false };

export const refreshDriver = createAsyncThunk("driver/refresh", async () => {
  const shift = await driverApi.currentShift();
  const tasks = shift?.status === "active" ? await driverApi.tasks() : [];
  return { shift, tasks };
});

const slice = createSlice({
  name: "driver",
  initialState,
  reducers: {
    setShift: (s, a: { payload: Shift | null }) => { s.shift = a.payload; },
    upsertTask: (s, a: { payload: DriverTask }) => {
      const i = s.tasks.findIndex((t) => t.id === a.payload.id);
      if (i >= 0) s.tasks[i] = { ...s.tasks[i], ...a.payload };
    },
    removeTask: (s, a: { payload: number }) => { s.tasks = s.tasks.filter((t) => t.id !== a.payload); },
  },
  extraReducers: (b) => {
    b.addCase(refreshDriver.fulfilled, (s, a) => { s.shift = a.payload.shift; s.tasks = a.payload.tasks; s.loaded = true; });
  },
});

export const { setShift, upsertTask, removeTask } = slice.actions;
export default slice.reducer;
