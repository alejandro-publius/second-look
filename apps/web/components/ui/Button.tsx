import Link from "next/link";

type Kind = "primary" | "secondary" | "quiet";

function classes(kind: Kind, block: boolean, extra?: string) {
  const k = kind === "primary" ? "" : kind === "secondary" ? " btn-secondary" : " btn-quiet";
  return `btn${k}${block ? " btn-block" : ""}${extra ? ` ${extra}` : ""}`;
}

/**
 * The only button in the product. A verb, never an arrow in the label, 48px tall, one accent.
 * It stays enabled until the request starts, which is what `busy` is for.
 */
export function Button({
  kind = "primary",
  block = false,
  busy = false,
  busyLabel,
  children,
  className,
  ...rest
}: {
  kind?: Kind;
  block?: boolean;
  busy?: boolean;
  busyLabel?: string;
  children: React.ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" {...rest} className={classes(kind, block, className)} aria-busy={busy || undefined}>
      {busy && busyLabel ? busyLabel : children}
    </button>
  );
}

/** Navigation uses a link, so a middle click and a long press behave the way people expect. */
export function ButtonLink({
  href,
  kind = "primary",
  block = false,
  children,
  ...rest
}: {
  href: string;
  kind?: Kind;
  block?: boolean;
  children: React.ReactNode;
} & Omit<React.ComponentProps<typeof Link>, "href" | "className">) {
  return (
    <Link href={href} {...rest} className={classes(kind, block)}>
      {children}
    </Link>
  );
}
