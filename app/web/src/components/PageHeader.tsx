import type { ReactNode } from "react";

interface Props {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: Props) {
  return (
    <div className="grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
      <div className="min-w-0">
        <div className="text-[10px] font-black uppercase tracking-[0.14em] text-brand">
          {eyebrow}
        </div>
        <h1 className="mt-0.5 max-w-full text-[26px] font-black leading-tight text-ink">
          {title}
        </h1>
        <p className="mt-1 max-w-[min(820px,100%)] text-sm leading-5 text-muted">
          {description}
        </p>
      </div>
      {actions && (
        <div className="flex min-w-0 max-w-full flex-wrap items-center justify-start gap-2 xl:justify-end">
          {actions}
        </div>
      )}
    </div>
  );
}
