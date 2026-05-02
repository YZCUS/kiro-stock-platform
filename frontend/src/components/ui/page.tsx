import type { ComponentType, ReactNode } from 'react';

import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

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
  tone?: 'neutral' | 'blue' | 'green' | 'red' | 'amber' | 'purple';
  className?: string;
}

const toneValueClasses = {
  neutral: 'text-gray-950',
  blue: 'text-blue-600',
  green: 'text-green-600',
  red: 'text-red-600',
  amber: 'text-amber-600',
  purple: 'text-purple-600',
};

const toneIconClasses = {
  neutral: 'text-gray-500',
  blue: 'text-blue-600',
  green: 'text-green-600',
  red: 'text-red-600',
  amber: 'text-amber-600',
  purple: 'text-purple-600',
};

export function PageShell({ children, className }: PageShellProps) {
  return (
    <main className={cn('mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8', className)}>
      {children}
    </main>
  );
}

export function PageHeader({ title, description, eyebrow, actions, className }: PageHeaderProps) {
  return (
    <header className={cn('flex flex-col gap-4 border-b border-gray-200 pb-5 lg:flex-row lg:items-end lg:justify-between', className)}>
      <div className="min-w-0">
        {eyebrow && <div className="mb-3">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-normal text-gray-950 sm:text-3xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600 sm:text-base">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {actions}
        </div>
      )}
    </header>
  );
}

export function PageSection({ title, description, actions, children, className }: PageSectionProps) {
  return (
    <section className={cn('space-y-3', className)}>
      {(title || description || actions) && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            {title && <h2 className="text-lg font-semibold text-gray-950">{title}</h2>}
            {description && <p className="mt-1 text-sm leading-6 text-gray-600">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function ToolbarPanel({ children, className }: PageShellProps) {
  return (
    <div className={cn('rounded-lg border border-gray-200 bg-white p-4 shadow-sm', className)}>
      {children}
    </div>
  );
}

export function MetricCard({ label, value, detail, icon: Icon, tone = 'neutral', className }: MetricCardProps) {
  return (
    <Card className={className}>
      <CardContent className="flex items-start justify-between gap-4 p-5">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <div className={cn('mt-1 text-2xl font-semibold', toneValueClasses[tone])}>
            {value}
          </div>
          {detail && <div className="mt-1 text-sm text-gray-500">{detail}</div>}
        </div>
        {Icon && <Icon className={cn('mt-1 h-5 w-5 shrink-0', toneIconClasses[tone])} />}
      </CardContent>
    </Card>
  );
}
