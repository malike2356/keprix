import { cn } from '@/lib/utils'

const assetPath = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`

type BrandVariant = 'color' | 'mono' | 'mono-inv'

// Brand badge: transparent crest by default (no baked tile / no white chip).
// Pass `flush={false}` only when a solid chip behind the mark is intentional.
export function BrandMark({
  className,
  variant = 'color',
  flush = true,
  ...props
}: React.ComponentProps<'span'> & { variant?: BrandVariant; flush?: boolean }) {
  const src = flush
    ? variant === 'mono'
      ? assetPath('logo-mono-clear.png')
      : variant === 'mono-inv'
        ? assetPath('logo-mono-inv-clear.png')
        : assetPath('logo-clear.png')
    : variant === 'mono'
      ? assetPath('logo-mono.png')
      : variant === 'mono-inv'
        ? assetPath('logo-mono-inv.png')
        : assetPath('logo.png')

  return (
    <span
      className={cn(
        'inline-flex size-14 shrink-0 items-center justify-center overflow-hidden',
        flush ? 'rounded-none bg-transparent' : 'rounded-md bg-white',
        className
      )}
      {...props}
    >
      <img alt="" className="size-full bg-transparent object-contain" src={src} />
    </span>
  )
}
