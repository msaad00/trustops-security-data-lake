import { toast } from "sonner";

/**
 * Thin wrapper over sonner so the app has one toast seam. Components call these
 * instead of hand-rolling fixed-position banners, so toasts stack, auto-dismiss,
 * and carry success/error styling consistently.
 */
export const notify = {
  success: (message: string) => toast.success(message),
  error: (message: string) => toast.error(message),
  message: (message: string) => toast(message),
};

export { toast };
