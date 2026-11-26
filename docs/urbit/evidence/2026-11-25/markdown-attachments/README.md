# Governed Markdown attachments

The follow-up distinguishes explicit safe image links, repository-relative images that require a clone, and unavailable targets. Alt text and canonical Markdown remain intact. Rendering creates no image element or automatic attachment request, and linked images expose a separate related link without nested anchors.

[Verification](verification.json): remote full TypeScript and 15 host tests passed (Markdown 4, attachments 6, product routes 5). Five additive Chromium reference cases passed: read-only modes, repository explanations, long descriptions at 320 px and 2× CSS zoom, and shared overflow keyboard/geometry/contrast. Targets measured 62 × 34 px on desktop and 56.796875 × 49.09375 px with narrow coarse pointer; contrast 16.169:1. All owned processes/profiles were removed, both locks released, and all eight live a0 services remained healthy.

The first browser failure is retained: its exact accessible-name expectation omitted whitespace around hidden text. Only two anchored name expectations changed; full wording and link/focus assertions remained. Product JS/CSS/HTML were unchanged. All five successor cases passed.

The tested maintained source baseline was 2280dcc7a00f972d6e33671d70386ada0344709f. The clean follow-up branch is based on a670d58c7801a48a92ab66139839fd192abbc53b and includes the nine attachment/reference files plus the two reviewed route dependency files, yielding the same production web bytes and host 15 inputs. Native sources and generated assets are unchanged; this is not a deployment.

[Scoped T02 acceptance](acceptance.json) combines the prior eight Firefox observations with these five additive observations and retains their separate source/session scope. No live-native, wider rollout or human-trial acceptance is implied. Screenshots were inspected and confirmed synthetic, but are retained privately with hashes in [custody](custody.json). The private font repertoire lacks some Unicode glyphs; source/DOM alt text remains complete.
