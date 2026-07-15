# Responsive UI Changes — Mobile & Tablet Support

This document explains every change made to make the platform work on phones and tablets.

---

## The Problem (Before)

The entire UI was **desktop-only**. On a phone:

- **Login page** — the branding panel and form panel sat side-by-side. The form panel was fixed at 460px wide, wider than most phone screens. Both panels overflowed horizontally.
- **Sidebar** — fixed at 260px wide, always visible. On a 375px phone (iPhone), it consumed 69% of the screen. The main content was squeezed into the remaining 115px. No way to hide it.
- **All forms** — used two-column grids (`1fr 300px`, `1fr 320px`, `1fr 340px`) with no media queries. The right panel, being a fixed pixel width, pushed content off-screen.
- **Tables** — wrapped in `overflow-x:auto` at best. No mobile layout alternatives.
- **No media queries** — zero `@media` rules in the entire CSS file (758 lines).
- **No touch support** — buttons were small (32-36px), hard to tap on a phone. Hover effects that never resolve on touch devices.

---

## Files Changed

| File | Change |
|------|--------|
| `static/css/style.css` | Added 202 lines: hamburger styles, sidebar overlay, login-outer wrapper, 2 media query blocks (`<900px`, `<480px`), touch optimisation |
| `templates/shared/base.html` | Added hamburger button in topbar, sidebar overlay div, JavaScript toggle function |
| `templates/authentication/login.html` | Added `login-outer` CSS class to the outer container |

---

## What Each Change Does

### 1. Hamburger Menu (`style.css` + `base.html`)

**Files:** `static/css/style.css` lines 763-795, `templates/shared/base.html` lines 117 + 124-127 + 166-171

What was added:

```
base.html:
  ┌─ <div id="sidebar-overlay">          ← dark backdrop
  └─ <button class="sidebar-toggle">     ← hamburger icon in topbar

style.css:
  .sidebar-toggle    → hidden on desktop, shown on mobile (36x36px button)
  .sidebar-overlay   → hidden on desktop, shown when sidebar is open (semi-transparent black)
  .sidebar           → on mobile: transform: translateX(-100%) slides it off-screen
  .sidebar.open      → transform: translateX(0) slides it back in
```

How it behaves:
- **Desktop (>900px)** — sidebar is always visible like before, hamburger is hidden
- **Mobile (<900px)** — sidebar is hidden off-screen to the left. Topbar shows a `` ☰ `` button
- **Tap ☰** → sidebar slides in from left, dark backdrop appears behind it
- **Tap a nav link or tap the backdrop** → sidebar slides back out
- **Transition** — smooth 0.3s slide animation

### 2. Login Page Responsive (`style.css` + `login.html`)

**Files:** `static/css/style.css` lines 798-802 + 835-847, `templates/authentication/login.html` line 5

The login page had a two-panel flex layout: branding panel (dark blue, 50% width) + form panel (white, 460px fixed width).

Change: the outer `<div>` now has `class="login-outer"`.

On mobile (<900px):
- The dark branding panel **is hidden** (it's decorative, not functional)
- The form panel becomes **full-width** (`width: 100%`, padding shrinks from 56px to 40px)
- The border-left that separated them is removed
- The form stretches to fill the whole screen height

### 3. Two-Column Grids → Single Column (`style.css`)

**File:** `static/css/style.css` lines 849-860

Every form page used inline styles like:
```html
<div style="display:grid; grid-template-columns:1fr 300px;">
```

On mobile, all of these collapse to single column using CSS selectors:

```css
.page-body [style*="grid-template-columns"][style*="px"] {
  grid-template-columns: 1fr !important;
}
.page-body [style*="grid-template-columns:1fr 1fr"] {
  grid-template-columns: 1fr !important;
}
```

This affects:
- Asset form (create/edit)
- User form and edit
- Org unit form
- Master data form  
- Asset category form
- Ministry form
- Pending access review
- Audit log detail
- Ministry detail (bottom section)

### 4. Stats Cards (Dashboard) (`style.css`)

**File:** `static/css/style.css` lines 862-866

Dashboard stat grid:
- **Desktop** — `repeat(auto-fit, minmax(200px, 1fr))` — auto-wraps based on container width
- **<900px** — `repeat(auto-fit, minmax(140px, 1fr))` — smaller minimum, so 2-3 cards fit per row
- **<480px** — `1fr` — single column, cards stack vertically

### 5. Filter Bar & Page Header (`style.css`)

**File:** `static/css/style.css` lines 868-896

- **Filter bar** — inputs already wrap via `flex-wrap`. On mobile, each filter input takes full width
- **Page header** — title + action button stack vertically instead of side-by-side
- **Card header** — same stacking behaviour for card title bars

### 6. Touch Optimisation (`style.css`)

**File:** `static/css/style.css` lines 946-962

Detects touch devices via `@media (hover: none) and (pointer: coarse)`:
- Sidebar links get extra top/bottom padding (11px → 44px tap target)
- Buttons get larger (11px padding top/bottom)
- Table row hover effects are removed (they cause confusion on touch — tap highlights a row but nothing happens)

### 7. Spacing & Typography (`style.css`)

**File:** `static/css/style.css` lines 883-889 + 910-940

- **<900px** — page body padding reduces from 28px to 16px, topbar padding reduces
- **<480px** — stat numbers get smaller (26px → 22px), table cells get less padding, button text shrinks slightly, schema badge font gets smaller

### 8. Table Scroll (`style.css`)

**File:** `static/css/style.css` lines 898-904

Added a `.table-responsive-wrap` utility class for smoother horizontal table scrolling on iOS (`-webkit-overflow-scrolling: touch`). Tables already had `overflow-x:auto` inline, so this is just a polish improvement.

---

## Breakpoint Summary

```
  0px         480px        900px               1920px
  ├─────────────┼─────────────┼─────────────────────┤
  │  PHONE      │   TABLET    │      DESKTOP        │
  │             │             │                      │
  │ Single-col  │ Compact     │ Full layout          │
  │ Sidebar     │ Sidebar     │ Sidebar always       │
  │ hidden,     │ hidden,     │ visible              │
  │ hamburger   │ hamburger   │                      │
  │             │             │                      │
  │ Login hides │ Login hides │ Login two-panel      │
  │ branding    │ branding    │                      │
  │             │             │                      │
  │ Stat cards  │ Stat cards  │ Stat cards           │
  │ 1 per row   │ 2-3 per row │ auto-wrap            │
```

## Verification Checklist

Test each of these on a phone (or Chrome DevTools with device emulation, Ctrl+Shift+M):

- [ ] Open login page on a 375px wide screen — branding panel hidden, form fills the screen
- [ ] Log in — sidebar is hidden, hamburger `` ☰ `` visible in top-left
- [ ] Tap ☰ — sidebar slides in from left with dark backdrop
- [ ] Tap a nav link — sidebar closes, page loads
- [ ] Tap backdrop — sidebar closes
- [ ] Open asset list — table scrolls horizontally, filter inputs full width
- [ ] Open asset form — all fields stack in single column
- [ ] Open dashboard — stat cards stack in 1-2 columns
- [ ] Open user list — table scrolls, page header buttons stack below title
- [ ] Rotate phone to landscape — sidebar should still work correctly
- [ ] Desktop (>900px) — everything looks like before, no changes
