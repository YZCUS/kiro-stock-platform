import type { ComponentType, ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type IconComponent = ComponentType<{ className?: string }>;

interface PageShellProps {
  children: ReactNode;
  className?: string;
}

interface PageHeaderProps {
  title: string;
  description?: string;
  eyebrow?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

interface PageSectionProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

interface MetricCardProps {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  icon?: IconComponent;
  tone?: "neutral" | "blue" | "green" | "red" | "amber" | "purple";
  className?: string;
}

const toneClasses = {
  neutral: {
    value: "text-foreground",
    icon: "border-border bg-muted text-muted-foreground",
  },
  blue: {
    value: "text-primary",
    icon: "border-primary/15 bg-primary/10 text-primary",
  },
  green: {
    value: "text-success",
    icon: "border-success/15 bg-success/10 text-success",
  },
  red: {
    value: "text-destructive",
    icon: "border-destructive/15 bg-destructive/10 text-destructive",
  },
  amber: {
    value: "text-warning",
    icon: "border-warning/15 bg-warning/10 text-warning",
  },
  purple: {
    value: "text-insight",
    icon: "border-insight/15 bg-insight/10 text-insight",
  },
};

export function PageShell({ children, className }: PageShellProps) {
  return (
    <div
      className={cn(
        "mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8 lg:py-7",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-4 border-b border-border pb-5 lg:flex-row lg:items-end lg:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow && <div className="mb-2.5">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-tight text-foreground lg:text-[1.75rem] lg:leading-9">
          {title}
        </h1>
        {description && (
          <p className="mt-1.5 max-w-3xl text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center [&>*]:w-full sm:[&>*]:w-auto">
          {actions}
        </div>
      )}
    </header>
  );
}

export function PageSection({
  title,
  description,
  actions,
  children,
  className,
}: PageSectionProps) {
  return (
    <section className={cn("space-y-3.5", className)}>
      {(title || description || actions) && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            {title && (
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {description}
              </p>
            )}
          </div>
          {actions && (
            <div className="flex flex-wrap items-center gap-2">{actions}</div>
          )}
        </div>
      )}
      {children}
    </section>
  );
}

export function ToolbarPanel({ children, className }: PageShellProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-4 shadow-panel",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
  className,
}: MetricCardProps) {
  const toneClass = toneClasses[tone];

  return (
    <Card className={className}>
      <CardContent className="flex items-start justify-between gap-4 p-5">
        <div className="min-w-0">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <div
            className={cn(
              "mt-1 text-2xl font-semibold tracking-tight tabular-nums",
              toneClass.value,
            )}
          >
            {value}
          </div>
          {detail && (
            <div className="mt-1 text-sm text-muted-foreground">{detail}</div>
          )}
        </div>
        {Icon && (
          <span
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-md border",
              toneClass.icon,
            )}
          >
            <Icon className="h-4 w-4" />
          </span>
        )}
      </CardContent>
    </Card>
  );
}
