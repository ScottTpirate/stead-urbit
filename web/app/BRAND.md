# Stead in the workspace

The Home header and its sign-in screen use the four closed paths supplied in the “Design Stead Logo” conversation and reproduced in `stead-mark-size-study.svg`. The master lives in `src/brandGeometry.ts`. Its four pieces form one place around an open center. The header pairs it at 28 px with the existing lowercase interface wordmark.

The master’s narrow vertical separation measures 3.44% of its width. At 16 px, that would occupy about half a pixel. The compact drawing widens both vertical seams to 1.5 units on a 16-unit grid. The browser favicon uses this drawing in parchment on a dark tile with a one-unit inset. Its resulting vertical gaps measure 1.31 px at 16 px. Run the normal browser build to reproduce `dist/favicon.svg` from that source.

The labeled project tabs reuse the compact drawing’s round shoulders, straight sides and square cuts. Overview shows the whole place. Work pairs stepped task markers with two rows. Docs opens two facing pages. Code uses two facing brackets. These four fixed symbols identify destinations. A member’s own Urbit sigil belongs alongside their name.

The header and section marks inherit the surrounding text color across themes. The favicon uses the existing House rail ink and background colors. Every clickable mark has a text label or an accessible control name. Keep the member sign-in approval and the project role visible in their established places.
