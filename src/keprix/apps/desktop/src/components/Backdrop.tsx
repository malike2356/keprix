import { Leva, useControls } from 'leva'
import { type CSSProperties, useEffect, useState } from 'react'

const BLEND_MODES = [
  'normal',
  'multiply',
  'screen',
  'overlay',
  'darken',
  'lighten',
  'color-dodge',
  'color-burn',
  'hard-light',
  'soft-light',
  'difference',
  'exclusion',
  'hue',
  'saturation',
  'color',
  'luminosity'
] as const

type BlendMode = (typeof BLEND_MODES)[number]
const assetPath = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`

/** Subtle Keprix crest watermark behind the chat canvas. */
export function Backdrop() {
  const [controlsOpen, setControlsOpen] = useState(false)

  useEffect(() => {
    if (!import.meta.env.DEV) {
      return
    }

    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null

      const editing =
        target?.isContentEditable ||
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement

      if (editing || event.repeat || event.altKey || event.ctrlKey || event.metaKey) {
        return
      }

      if (event.shiftKey && event.code === 'KeyY') {
        setControlsOpen(open => !open)
      }
    }

    window.addEventListener('keydown', onKeyDown)

    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const shape = useControls(
    'UI / Shape',
    { radiusScalar: { value: 0.2, min: 0, max: 2, step: 0.1, label: 'radius scalar' } },
    { collapsed: true }
  )

  useEffect(() => {
    document.documentElement.style.setProperty('--radius-scalar', String(shape.radiusScalar))
  }, [shape.radiusScalar])

  const mark = useControls(
    'Backdrop / Crest',
    {
      enabled: { value: true, label: 'on' },
      opacity: { value: 0.06, min: 0, max: 0.35, step: 0.005 },
      blendMode: { value: 'soft-light' as BlendMode, options: BLEND_MODES, label: 'blend' },
      scale: { value: 72, min: 30, max: 140, step: 1, label: 'size (vmin)' },
      offsetX: { value: 8, min: -40, max: 40, step: 1, label: 'offset x %' },
      offsetY: { value: 4, min: -40, max: 40, step: 1, label: 'offset y %' }
    },
    { collapsed: true }
  )

  return (
    <>
      <Leva collapsed hidden={!import.meta.env.DEV || !controlsOpen} titleBar={{ title: 'backdrop', drag: true }} />

      {mark.enabled ? (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-2 overflow-hidden"
          style={{
            mixBlendMode: mark.blendMode as CSSProperties['mixBlendMode'],
            opacity: mark.opacity
          }}
        >
          <img
            alt=""
            className="absolute left-1/2 top-1/2 max-w-none select-none object-contain"
            fetchPriority="low"
            src={assetPath('logo-trans.png')}
            style={{
              width: `${mark.scale}vmin`,
              height: `${mark.scale}vmin`,
              transform: `translate(calc(-50% + ${mark.offsetX}%), calc(-50% + ${mark.offsetY}%))`
            }}
          />
        </div>
      ) : null}
    </>
  )
}
