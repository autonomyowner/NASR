## Hero Revamp Plan (Home Page)

### Goals
- **Clean, fresh first impression** on a light aqua background; no glass card.
- **Clear value prop** via concise headline and supporting line.
- **Improved type hierarchy** using a display font for headings.
- **Delight** with a lightweight typewriter effect on secondary phrase.

### Copy (draft)
- **Badge**: WEBSITE / Early Access
- **Headline**: Your end‑to‑end Language Partner
- **Subheadline**: Real‑time voice and text translation that connects people instantly.
- **CTAs**: Primary “Try Travoice”, Secondary “Learn More”
- **Stats**: “<5s Translation Speed”, “50+ Languages”, “Web Based Platform”

### Visual Direction
- **Background**: flat/light with subtle noise and faint grid; no glass surface.
- **Motion**: gentle fade/slide on load; heading typewriter effect.

### Typography
- **Headings**: Playfair Display; tighter leading on desktop.
- **Body**: Inter.
- **Scale**: H1 40–56px mobile → 72–80px desktop; subhead 18–24px.

### Layout
- **Container**: max‑w‑6xl centered; min‑h‑screen; generous spacing.
- **Order**: Badge → H1 → Subhead → Stats row → CTAs.
- **Stats**: three lightweight cards; wrap on small screens.

### Accessibility
- Maintain AA contrast; visible focus rings; semantic `<section>` + `<h1>`.

### Tasks
1) Add display font utilities and colors per palette below.
2) Refactor `src/components/Hero.tsx` with new copy and structure.
3) Implement light background + faint grid + optional noise (no glass surface).
4) Add typewriter effect for rotating phrase using TypeScript component.
5) Style stats cards and responsive behavior.
6) Verify accessibility and responsive spacing across breakpoints.

### Acceptance Checklist
- [x] Light aqua background with faint grid; no glass card.
- [x] Typewriter effect runs smoothly and is accessible.
- [x] Updated headline/subheadline/CTAs render correctly on all breakpoints.
- [x] Stats row responsive and consistent.
- [x] H1 uses Playfair Display; body uses Inter.
- [x] Basic a11y (focus, contrast) verified.

### Color Palette (exact)
- **Background primary**: `#D3E3E0`
- **Background secondary/section**: `#74B3A5`
- **Text primary**: `#4A6C5C`
- **Text secondary**: `#5B9179`
- **Accent primary (CTAs)**: `#6EA294`
- **Accent hover/active**: `#689587`
- **Optional contrast accent**: Coral `#FF6F61` or Golden Yellow `#F2C94C` (sparingly)

### Copy (updated)
- **Headline**: Your end‑to‑end Language Partner
- **Typewriter phrase**: [Translate • Transcribe • Connect Globally]
- **Subheadline**: Real‑time voice and text translation that connects people instantly.
- **CTAs**: Primary “Start Translating”, Secondary “See How It Works”

