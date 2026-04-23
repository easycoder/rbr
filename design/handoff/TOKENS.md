# Tokens — Room By Room

Quick reference. Paste into your Webson constants file. Names are suggestions; keep whatever naming scheme your codebase already uses.

## Colour

```
color.accent            = #E86A33   // primary warm orange; tweakable
color.accent.8          = #E86A3314  // 8% opacity
color.accent.10         = #E86A331A  // 10% opacity
color.accent.12         = #E86A331F  // 12% opacity
color.accent.20         = #E86A3333  // 20% opacity
color.accent.tintedShadow = rgba(232,106,51,0.25)   // house-mark drop

color.text.primary      = #1A1A1A
color.text.secondary    = #666666
color.text.muted        = #999999
color.text.meta         = #AAAAAA
color.text.disabled     = #BBBBBB

color.surface.card      = #FFFFFF
color.surface.sunk      = #F4F5F7   // segmented-control background
color.surface.pill      = #FAFAFA   // profile pill background

color.chip.neutral.bg   = #F1F3F5
color.chip.neutral.fg   = #999999
color.chip.ok.bg        = #E8F4EC
color.chip.ok.fg        = #3A8C5F
color.chip.warn.bg      = #FFF4E0
color.chip.warn.fg      = #C78A1A
color.chip.heat.bg      = #E86A3314    // accent/8
color.chip.heat.fg      = #E86A33      // accent

color.border.hairline   = #ECECEC
color.border.divider    = #F0F0F0
color.border.dividerSoft = #F3F3F3

color.status.heating    = #E86A33     // = accent
color.status.warn       = #C78A1A
color.scrim             = rgba(0,0,0,0.35)
```

## Time-of-day gradient

Three stops, top → mid → bottom.

```
gradient.night      = [ #1E2238, #2D2A3E, #433048 ]   // 00:00–05:59, 22:00–23:59
gradient.morning    = [ #FFE8D4, #FFD3B0, #F5B994 ]   // 06:00–09:59
gradient.midday     = [ #FDF6EC, #FBEEDD, #F5E2C9 ]   // 10:00–14:59
gradient.afternoon  = [ #FFE1C2, #F7B88A, #E88A5B ]   // 15:00–18:59
gradient.sunset     = [ #F0A877, #B66B56, #5A3A52 ]   // 19:00–21:59

gradient.overlay    = radial(ellipse at 50% -20%, rgba(255,255,255,0.5) 0%, transparent 70%)
```

## Typography

Stack: `-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif`.

```
type.appName        = 17 / 600 / -0.3
type.sheetTitle     = 17 / 600 / -0.3
type.summaryTitle   = 15 / 600 / -0.2
type.roomName       = 16 / 600 / -0.2          // 15 in compact density
type.currentTemp    = 22 / 500 / -0.8          // 20 in compact
type.targetBig      = 30 / 500 / -1.0
type.statValue      = 18 / 600 / -0.3
type.statDate       = 14 / 600 / -0.3
type.body           = 13–14 / 500
type.subLine        = 12 / 400–500
type.caption        = 11 / 400
type.sectionLabel   = 10.5 / 500 / +0.4 / UPPERCASE
```

Numbers are `size / weight / letter-spacing (px)`.

## Spacing, radius, shadow

```
space.pageX         = 16
space.pageY.top     = 14
space.cardPad       = 14–18
space.rowGap        = 8

radius.card         = 16
radius.sheet        = 24
radius.summary      = 20
radius.button       = 10–12
radius.chip         = 10–12
radius.segmentItem  = 9
radius.targetTile   = 14
radius.stepBtn      = 17        // 54×54 discs

shadow.card         = 0 1px 2px rgba(0,0,0,0.04), 0 4px 14px -8px rgba(0,0,0,0.08)
shadow.cardRaised   = 0 1px 2px rgba(0,0,0,0.05), 0 12px 32px -8px rgba(0,0,0,0.12)
shadow.stepBtn      = 0 1px 2px rgba(0,0,0,0.06), 0 6px 16px -6px rgba(0,0,0,0.14)
shadow.sheet        = 0 -12px 40px -8px rgba(0,0,0,0.2)
shadow.houseMark    = 0 4px 12px rgba(232,106,51,0.25)
```

## Motion

```
motion.chevronRotate   = 0.25s
motion.sheetSlide      = 0.28s cubic-bezier(.2, .9, .3, 1)
motion.scrimFade       = 0.24s
motion.buttonPress     = scale(0.98) 50ms
motion.heatingPulse    = box-shadow 1.6s infinite (decorative)
```

## Temperature semantics

```
temp.min               = 5.0    // °C
temp.max               = 30.0
temp.step              = 0.5
temp.deadband          = 0.2    // target - temp must exceed this to "call for heat"
```

## Touch targets

- Minimum: **44 × 44** (iOS baseline).
- Applied: step buttons 54 × 54; menu button 38 × 38; segmented pills height ≈ 40; boost chips height ≈ 40.
