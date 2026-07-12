import type { ReactNode } from "react";

interface Props {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: Props) {
  return (
    <div className="grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
      <div className="min-w-0">
        <div className="ui-eyebrow">{eyebrow}</div>
        <h1 className="ui-page-title mt-0.5 max-w-full">{title}</h1>
        {description ? (
          <p className="mt-1 max-w-[min(720px,100%)] text-sm leading-5 text-muted">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex min-w-0 max-w-full flex-wrap items-center justify-start gap-2 lg:justify-end">
          {actions}
        </div>
      ) : null}
    </div>
  );
}
