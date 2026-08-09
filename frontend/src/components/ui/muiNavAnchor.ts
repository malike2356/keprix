/**
 * MUI in-app navigation policy (Keprix frontend)
 *
 * Prefer MUI component="a" with an href for in-app navigation.
 * Do not pass next/link (imported as Link or NextLink) as the MUI `component`
 * prop on Button, Box, Tab, CardActionArea, ListItemButton, Typography, or MenuItem.
 *
 * Why: Next soft navigation through MUI + next/link can stick and freeze menus
 * (dead clicks). Plain anchors avoid that. See Sidebar.tsx and OutreachTabNav.
 *
 * Still fine: wrapping with a next/link JSX element when it is not passed as a
 * MUI `component` prop; external links already using component="a".
 *
 * This module exports nothing; it documents the policy for reviewers and for
 * `src/lib/__tests__/mui-nav-anchor-policy.test.ts`.
 */

export {};
