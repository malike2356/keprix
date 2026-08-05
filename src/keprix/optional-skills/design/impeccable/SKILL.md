# Impeccable

Use this skill when improving a selected UI component from Keprix Design Live Preview.

## Checklist

1. Preserve the component's behavior, labels, and data bindings unless the user asks for a change.
2. Fix layout density first: spacing rhythm, alignment, sizing, and responsive constraints.
3. Use a restrained type scale. Avoid viewport-scaled font sizes and negative letter spacing.
4. Check contrast for text, borders, focus states, and disabled states.
5. Make interactive states explicit: hover, focus-visible, active, loading, empty, and error.
6. Keep controls familiar: icons for common actions, menus for option sets, toggles for booleans.
7. Do not add decorative gradients, blobs, or marketing-style hero treatment inside tools.
8. Return a concrete patch plan or code diff scoped to the selected component.

## Selection Context

Design Live Preview supplies:

- preview session id
- file context
- CSS selector
- selected HTML snippet
- bounding box and class metadata

Use that context to improve the selected surface without broad unrelated refactors.
