import { notify } from "@/lib/toast";

/** Route connector drawer / cloud-link messages to success vs error toasts. */
export function connectorNotify(message: string) {
  const lower = message.toLowerCase();
  if (
    lower.includes("failed") ||
    lower.includes("error") ||
    lower.includes("required") ||
    lower.includes("invalid") ||
    lower.includes("must be") ||
    lower.startsWith("probe error") ||
    lower.includes("before enabling") ||
    lower.includes("could not copy") ||
    lower.includes("contract-only")
  ) {
    notify.error(message);
    return;
  }
  notify.success(message);
}
