import Image from "next/image";

const SIZES = { sm: 20, md: 28, lg: 32 } as const;

type Size = keyof typeof SIZES;

export function LogoMark({
  size = "md",
  className = "",
}: {
  size?: Size;
  className?: string;
}) {
  const px = SIZES[size];
  return (
    <Image
      src="/logo.png"
      alt=""
      width={px}
      height={px}
      className={`shrink-0 object-contain ${className}`}
      priority={size === "lg"}
    />
  );
}

export function Logo({
  variant = "app",
  showWordmark = true,
  className = "",
}: {
  variant?: "landing" | "app";
  showWordmark?: boolean;
  className?: string;
}) {
  const isLanding = variant === "landing";
  return (
    <span
      className={`flex items-center gap-2 font-semibold tracking-tight ${
        isLanding ? "text-[19px]" : ""
      } ${className}`}
    >
      <LogoMark size={isLanding ? "lg" : "md"} />
      {showWordmark && (
        <span
          className={
            isLanding
              ? "ital text-[color:var(--ink)]"
              : "serif-accent text-[18px]"
          }
        >
          Sprout
        </span>
      )}
    </span>
  );
}
