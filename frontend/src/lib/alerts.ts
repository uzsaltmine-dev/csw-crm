import Swal from "sweetalert2";

const base = { confirmButtonColor: "#1d6b4f", heightAuto: false } as const;

export const toast = (title: string, icon: "success" | "error" | "warning" | "info" = "success") =>
  Swal.fire({ ...base, toast: true, position: "top", timer: 3500, showConfirmButton: false, icon, title });

export const confirmDialog = (title: string, confirmText: string, cancelText: string, text?: string) =>
  Swal.fire({ ...base, title, text, icon: "question", showCancelButton: true, confirmButtonText: confirmText, cancelButtonText: cancelText })
    .then((r) => r.isConfirmed);
