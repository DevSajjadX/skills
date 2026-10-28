# Web probes

Checks worth running on most web apps, after the adapter's own journeys. For a broader UX checklist, `agent-browser skills get dogfood` has an issue taxonomy.

- **Signed-out redirects.** Open a protected page with no session: note the status and the landing URL, then sign in and check you return to the page asked for. A redirect that replays a form post at the sign-in page (a 307 or 308 where a 302 or 303 belongs) is a bug.
- **Two tabs, two contexts.** Where a user can switch account, workspace or company, switch in one tab and save in the other. The save must land where that tab says it is, and no tab may show the old context's data after a switch.
- **Roles.** Repeat a privileged page and its actions as a lower role: the page and its data must refuse, not just hide the button.
- **Forms.** Submit empty, too long, mixed scripts and digits (Latin, Persian, Arabic where the product serves them), and pasted whitespace. Each error sits next to its field and says what to do; the typed values survive the error.
- **Lists.** Empty state on a fresh account; page to the end; add a row while paging and check nothing repeats or vanishes; filters and search survive a reload when the product says they should.
- **Persistence.** After every save, reload and open the item fresh.
- **Locale and direction.** Switch language: the address behaves as the product says, and the choice survives a reload, a new tab and signing out and in. Under right-to-left, icons and margins mirror; dates, digits and numbers follow the locale.
- **Narrow screen.** Repeat the main journeys at 375 px wide (`agent-browser set viewport 375 812`): no sideways page scroll, every control reachable, tables scroll or stack.
- **Screen vs response.** For anything numeric or listed, compare what the screen shows with what the network returned. Wrong on screen and right in the response is a rendering bug; wrong in the response is an API bug (`api-probes.md`).
