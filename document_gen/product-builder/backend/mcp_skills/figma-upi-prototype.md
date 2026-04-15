---
name: UPI Design Figma Prototypes 
description: Use this skill to orchestrate Figma design workflows to generate standard UPI prototypes and mobile app screens.
---
# Figma UPI Prototype Skill

When requested to build a UPI prototype or UI screens in Figma:
1. Initialize a new mobile frame (e.g., iPhone 15 Pro size).
2. Utilize the NPCI design system colors:
   - Primary: Indigo (`#4F2D7F`)
   - Accent: Orange (`#F58220`)
   - Success: Emerald Green (`#10B981`)
   - Backgrounds: White & Slate-50
   - Text: High contrast Slate-900 for headings, Slate-500 for secondary text
3. Ensure components include standard UPI elements:
   - App Header with UPI Logo or App Name
   - Clear Account Balance or Transaction Amount
   - Trust seals / "Powered by NPCI" footer where applicable
   - Call to Action (CTA) buttons must be highly visible and use the primary or accent colors.
4. Structure the layers properly and apply Auto Layout for responsive constraints.

You should use this context alongside `use_figma` and `<generate_figma_design>` tools provided by the Figma MCP server.
