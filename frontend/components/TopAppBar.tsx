import { Icon } from './Icon';

interface TopAppBarProps {
  title: string;
  subtitle?: string;
  online?: boolean;
}

export function TopAppBar({ title, subtitle, online }: TopAppBarProps) {
  return (
    <header className="sticky top-0 z-40 flex w-full items-center justify-between bg-surface/95 px-4 py-2 shadow-sm backdrop-blur-md">
      <div className="flex items-center gap-2.5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-container text-on-primary-container">
          <Icon name="elderly" className="text-[24px]" />
        </div>
        <div className="flex flex-col">
          <h1 className="text-lg font-semibold leading-tight tracking-tight text-primary">
            {title}
          </h1>
          {subtitle ? (
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="text-xs text-on-surface-variant">
                Monitoring: <strong className="font-semibold text-on-surface">{subtitle}</strong>
              </span>
              {online !== undefined && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium leading-none text-emerald-800">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  {online ? 'Online' : 'Offline'}
                </span>
              )}
            </div>
          ) : null}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          aria-label="Notifikasi"
          type="button"
          className="relative flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container active:scale-95"
        >
          <Icon name="notifications" className="text-[24px]" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-error" />
        </button>
        <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-surface-container-high ring-2 ring-surface-container-highest">
          <Icon name="person" className="text-[22px] text-on-surface-variant" />
        </div>
      </div>
    </header>
  );
}
