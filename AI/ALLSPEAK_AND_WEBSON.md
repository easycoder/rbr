# AllSpeak + Webson Guide (for AI)

## AllSpeak style in this repo
- Treat `.as` as the source of high-level behaviour
- Make surgical changes; preserve command vocabulary and flow
- Prefer existing labels/subroutines over introducing new structures

## Typical AllSpeak operations seen here
- `attach` / `create` / `set` / `enable` / `disable`
- `on click` / `on change` handlers
- JSON helpers (`json split`, `json count`, `json index`, etc.)
- MQTT `send` / `receive` and state branching
- `render WEBSON_LAYOUT in CONTAINER`

## Webson usage here
- Legacy UI: `resources/webson/*.json` defines screen layouts with element IDs
- New UI (PWA): `new-ui/resources/webson/*.json` defines the new app's layouts
- AllSpeak attaches to elements by their `@id` values
- Renaming IDs requires matching changes in `.as` files (all `attach` and `on click` references)
- Renaming only Webson object keys (not `@id`) is safe if IDs stay stable

## RBR-specific Webson conventions
- Every element object needs `#element`
- Element IDs use `@id` (never plain `id`)
- Children go in the `#` key; child definitions prefixed with `$`
- Style properties go directly on the element object (no nested `style` object)

## Compatibility note
When targeting older runtimes, avoid `??` and similar modern JS syntax unless the build target is upgraded.
