import { useEffect, useState } from "react";
import type { Coords } from "@/types";

export type GeoState = { coords: Coords | null; error: "denied" | "unavailable" | null };

/** Jonli GPS: ekran ochiq turganda navigator.geolocation.watchPosition. */
export function useGeolocation(enabled = true): GeoState {
  const [state, setState] = useState<GeoState>({ coords: null, error: null });
  useEffect(() => {
    if (!enabled) return;
    if (!("geolocation" in navigator)) { setState({ coords: null, error: "unavailable" }); return; }
    const id = navigator.geolocation.watchPosition(
      (p) => setState({ coords: { lat: p.coords.latitude, lng: p.coords.longitude, accuracy: Math.round(p.coords.accuracy) }, error: null }),
      (e) => setState((s) => ({ ...s, error: e.code === e.PERMISSION_DENIED ? "denied" : "unavailable" })),
      { enableHighAccuracy: true, maximumAge: 10_000, timeout: 30_000 },
    );
    return () => navigator.geolocation.clearWatch(id);
  }, [enabled]);
  return state;
}

export function distanceM(a: Coords, b: Coords): number {
  const R = 6_371_000, rad = (x: number) => (x * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(h)));
}
