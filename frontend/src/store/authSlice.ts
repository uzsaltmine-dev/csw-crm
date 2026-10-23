import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { authApi } from "@/api/endpoints";
import { errorCode } from "@/api/client";
import type { User } from "@/types";

interface AuthState { user: User | null; status: "unknown" | "loading" | "ready"; error: string | null }
const initialState: AuthState = { user: null, status: "unknown", error: null };

export const loadMe = createAsyncThunk("auth/me", async () => {
  try { return await authApi.me(); } catch { return null; }
});

export const login = createAsyncThunk<User, { username: string; password: string }, { rejectValue: string }>(
  "auth/login",
  async ({ username, password }, { rejectWithValue }) => {
    try { return await authApi.login(username, password); } catch (e) { return rejectWithValue(errorCode(e)); }
  },
);

export const logout = createAsyncThunk("auth/logout", async () => {
  try { await authApi.logout(); } catch { /* sessiya baribir tozalanadi */ }
});

const slice = createSlice({
  name: "auth",
  initialState,
  reducers: { sessionExpired: (s) => { s.user = null; s.status = "ready"; } },
  extraReducers: (b) => {
    b.addCase(loadMe.pending, (s) => { s.status = "loading"; })
      .addCase(loadMe.fulfilled, (s, a) => { s.user = a.payload; s.status = "ready"; })
      .addCase(login.pending, (s) => { s.error = null; })
      .addCase(login.fulfilled, (s, a) => { s.user = a.payload; s.status = "ready"; })
      .addCase(login.rejected, (s, a) => { s.error = a.payload ?? "unknown"; })
      .addCase(logout.fulfilled, (s) => { s.user = null; });
  },
});

export const { sessionExpired } = slice.actions;
export default slice.reducer;
