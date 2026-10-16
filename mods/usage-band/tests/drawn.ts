// The text a Client's module drew, one string per band row (the module draws a column of rows).
type El = { type?: string; props?: { children?: unknown } & Record<string, unknown>; children?: unknown }

const textOf = (n: unknown): string => {
  if (typeof n === 'string' || typeof n === 'number') return String(n)
  if (Array.isArray(n)) return n.map(textOf).join('')
  if (n && typeof n === 'object') {
    const el = n as El
    return textOf(el.children ?? el.props?.children)
  }
  return ''
}

const kids = (n: unknown): unknown[] => {
  const el = n as El
  const c = el?.children ?? el?.props?.children
  return Array.isArray(c) ? c : c === undefined ? [] : [c]
}

export const bandRows = (drawn: unknown): string[] => kids(drawn).map(textOf)

// The cell column of the card in `row` whose text contains `label`: margins and widths summed,
// as the surface lays the row out.
export function cardX(drawn: unknown, row: number, label: string): number {
  let x = 0
  for (const card of kids(kids(drawn)[row])) {
    const p = ((card as El).props ?? {}) as { width?: number; marginLeft?: number }
    x += p.marginLeft ?? 0
    if (textOf(card).includes(label)) return x + 1
    x += p.width ?? 0
  }
  return -1
}
