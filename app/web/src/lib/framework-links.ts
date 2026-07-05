export function frameworkDetailHref(
  frameworkId: string,
  controlId?: string | null,
): string {
  const params = new URLSearchParams({ framework: frameworkId });
  if (controlId) params.set("control", controlId);
  return `/frameworks?${params.toString()}`;
}
