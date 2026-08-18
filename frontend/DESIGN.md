---
name: Synthesized Intelligence
colors:
  surface: '#fcf8fa'
  surface-dim: '#dcd9db'
  surface-bright: '#fcf8fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f5'
  surface-container: '#f0edef'
  surface-container-high: '#eae7e9'
  surface-container-highest: '#e4e2e4'
  on-surface: '#1b1b1d'
  on-surface-variant: '#45464d'
  inverse-surface: '#303032'
  inverse-on-surface: '#f3f0f2'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#271901'
  on-tertiary-container: '#98805d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#fcdeb5'
  tertiary-fixed-dim: '#dec29a'
  on-tertiary-fixed: '#271901'
  on-tertiary-fixed-variant: '#574425'
  background: '#fcf8fa'
  on-background: '#1b1b1d'
  surface-variant: '#e4e2e4'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  code-sm:
    fontFamily: jetbrainsMono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 20px
  margin: 24px
  max-width: 1440px
---

## Brand & Style
The design system is built for high-stakes decision-making environments. It communicates authority, precision, and objectivity through an **Enterprise Modern** aesthetic. The personality is "Calculated Confidence"—a balance between the rigid structure required for recruitment compliance and the fluid, innovative nature of AI.

The visual direction prioritizes data density without sacrificing clarity. It utilizes a refined color palette and generous white space to reduce cognitive load during complex evaluation tasks. The goal is to evoke a sense of "Unbiased Clarity" for recruiters and hiring managers.

## Colors
The palette is anchored by **Deep Navy (#0F172A)**, used for primary navigation and high-level structural elements to establish immediate trust. The **Intelligence Blue (#3B82F6)** serves as the primary action color and signifies AI-driven insights or "matching" logic.

**Slate Gray (#64748B)** is utilized for secondary information and labels to maintain a clean visual hierarchy. For status indicators, the system uses semantic colors (Success Green, Warning Amber, Danger Red) to provide instant feedback on candidate status and evaluation scores. Data visualizations should pull from the accent blue and its lighter tints to maintain a cohesive "intelligent" feel.

## Typography
This design system utilizes **Inter** for all functional and display text to leverage its exceptional legibility at small sizes, which is critical for data-heavy recruitment tables. 

**Headlines** use a tighter letter-spacing and bold weights to ground the page. **Body text** defaults to 14px for standard data entry and 16px for long-form candidate summaries. **Labels** are treated with a slightly heavier weight and uppercase styling to distinguish them from dynamic data. For technical metadata or system-generated IDs, use a monospaced font like **JetBrains Mono** at a reduced scale.

## Layout & Spacing
The system employs a **Fixed-Fluid Hybrid Grid**. For the main dashboard, use a 12-column grid with a maximum container width of 1440px. Gutters are fixed at 20px to ensure data columns remain distinct.

- **Desktop:** 12 columns, 24px side margins. Large sidebars for navigation (fixed at 260px).
- **Tablet:** 8 columns, 16px side margins. Sidebars collapse to icons.
- **Mobile:** 4 columns, 12px side margins. Data tables should transition to card-based layouts.

Vertical rhythm follows a 4px baseline, but primary components should be spaced using 16px (md) increments to maintain a professional, airy feel despite the high density of information.

## Elevation & Depth
Depth is created through **Tonal Layering** supplemented by subtle **Ambient Shadows**. This approach ensures the UI feels modern and multi-dimensional without the clutter of heavy borders.

- **Level 0 (Background):** #F8FAFC. The canvas.
- **Level 1 (Surface):** #FFFFFF. Used for main content cards and table rows. Features a 1px border of #E2E8F0.
- **Level 2 (Raised):** Used for hover states on cards and dropdown menus. Shadow: `0px 4px 6px -1px rgba(15, 23, 42, 0.1), 0px 2px 4px -1px rgba(15, 23, 42, 0.06)`.
- **Level 3 (Overlay):** Used for modals and slide-outs. Shadow: `0px 20px 25px -5px rgba(15, 23, 42, 0.1), 0px 10px 10px -5px rgba(15, 23, 42, 0.04)`.

Avoid high-contrast shadows; instead, use the Deep Navy primary color at low opacities to tint the shadows for a more integrated, sophisticated appearance.

## Shapes
The design system follows a **Rounded** (Level 2) logic. A standard radius of **8px (0.5rem)** is applied to buttons, input fields, and cards. This softens the "corporate" edge while maintaining a disciplined, structured look.

- **Small elements (chips, checkboxes):** 4px.
- **Standard components (buttons, inputs, cards):** 8px.
- **Large containers (modals, hero sections):** 16px.
- **Avatars:** Always circular (full rounding) to contrast with the geometric layout.

## Components
- **Buttons:** Primary buttons use the Intelligence Blue background with white text. Secondary buttons use a white background with a Slate Gray border. 
- **Input Fields:** Use 8px rounding with a 1px border (#CBD5E1). On focus, the border shifts to Blue (#3B82F6) with a subtle 2px outer glow.
- **Chips/Badges:** Used for candidate skills and tags. Use a "Soft" roundedness (4px) with a light tinted background of the category color (e.g., light blue for "Technical," light purple for "Soft Skills").
- **Cards:** The primary container for candidate profiles and evaluation summaries. White background, 1px border, 8px corner radius.
- **Skill Radar Charts:** Use Intelligence Blue for the area fill with 20% opacity. Data points should be marked with solid Blue dots.
- **Status Timeline:** A vertical stepper using 8px nodes. Completed steps are solid Success Green; current steps are Blue outlines; future steps are Slate Gray.
- **Data Tables:** High density. Use 12px vertical padding. Header rows use a light navy background (#F1F5F9) and bold 12px labels.