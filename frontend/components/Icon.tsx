interface IconProps {
  name: string;
  filled?: boolean;
  className?: string;
}

export function Icon({ name, filled, className }: IconProps) {
  return (
    <span
      aria-hidden="true"
      className={`material-symbols-outlined${
        filled ? ' material-symbols-fill' : ''
      } ${className ?? ''}`}
    >
      {name}
    </span>
  );
}
