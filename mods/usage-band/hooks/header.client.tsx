// A details-pane card's header row: the whole row opens and closes its card (a Button takes a
// press only on its own label). No `$` here: the hooks module's ui.message hook does the toggle.
import type { ClientSurface } from 'claude-code'

type Props = { id: string; title: string; summary: string; open: boolean }
type State = { hover?: boolean }

export default function Header(props: Props, surface: ClientSurface<State>) {
  const { Box, Text } = surface.elements
  surface.onPointer(e => {
    if (e.type === 'up' && e.button === 'left') surface.post({ toggle: props.id })
    const hover = e.type === 'leave' ? false : e.type === 'enter' || e.type === 'move' ? true : surface.state?.hover
    if (hover !== surface.state?.hover) surface.setState({ hover })
  })
  return (
    <Box flexDirection="row" justifyContent="space-between" width="100%">
      <Text>
        {/* One triangle pair: › and ⌄ sit on different baselines in the desktop's font. */}
        <Text dimColor>{props.open ? '▾  ' : '▸  '}</Text>
        <Text bold>{props.title}</Text>
      </Text>
      {!props.open && <Text dimColor={!surface.state?.hover}>{props.summary}</Text>}
    </Box>
  )
}
