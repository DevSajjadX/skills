// An invisible strip laid over one row of the band's cards (the SVG takes no clicks). The desktop
// reports a strip as one row tall whatever its pixels, so the row is which strip got the click, and
// only the column is read: its share of the strip is the same share of the drawing's width.
import type { ClientSurface } from 'claude-code'

import { SECTION } from './cells'
import type { CardRect } from './pills'

type Props = { boxes: CardRect[]; width: number }
// A click in the gap between cards goes to a card this close, in drawing pixels (the gap is 6).
const NEAR_PX = 8

// The card under x, or the nearest one when the click falls in the gap between two.
export function cardAt(boxes: readonly CardRect[], x: number): CardRect | undefined {
  const inside = boxes.find(b => x >= b.x && x < b.x + b.w)
  if (inside) return inside
  const dist = (b: CardRect) => (x < b.x ? b.x - x : x - (b.x + b.w))
  const near = [...boxes].sort((a, b) => dist(a) - dist(b))[0]
  return near && dist(near) <= NEAR_PX ? near : undefined
}

export default function Hit(props: Props, surface: ClientSurface) {
  const { Box } = surface.elements
  surface.onPointer(e => {
    if (e.type !== 'up' || e.button !== 'left' || surface.columns === 0) return
    const x = ((e.fine?.x ?? e.x + 0.5) / surface.columns) * props.width
    const card = cardAt(props.boxes, x)
    if (card) surface.post({ open: SECTION[card.tone] })
  })
  return <Box width="100%" height="100%" />
}
