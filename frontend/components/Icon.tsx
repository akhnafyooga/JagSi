interface IconProps {
  name: string;
  filled?: boolean;
  className?: string;
}

const SIZE_CLASS = /(?:^|\s)text-\[(\d+(?:\.\d+)?)px\](?=\s|$)/;

/**
 * Material Symbols icon.
 *
 * The size is also applied inline. Google's icon stylesheet is loaded after the
 * app's CSS and sets `font-size: 24px` on `.material-symbols-outlined`, so until
 * Week 8 every `text-[..px]` size on an icon lost and all icons were 24 px
 * (the 40 px SOS button and the emergency screen's 56 px icon included).
 */
export function Icon({ name, filled, className }: IconProps) {
  const size = SIZE_CLASS.exec(className ?? '')?.[1];
  return (
    <span
      aria-hidden="true"
      style={size ? { fontSize: `${size}px` } : undefined}
      className={`material-symbols-outlined${
        filled ? ' material-symbols-fill' : ''
      } ${className ?? ''}`}
    >
      {name}
    </span>
  );
}
