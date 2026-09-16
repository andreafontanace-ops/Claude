# HyperFrames layer

Remotion owns these films: the geodata, the camera, the timeline. What it does
not own is every look worth having, and the HyperFrames registry has about 400
of them. This directory is where those get made.

The two frameworks are not alternatives here. They meet in two places.

## 1. Ported, no render (`src/shared/GrainOverlay.tsx`)

Registry items that are pure CSS can move into Remotion as components. The only
real problem is the clock: a CSS animation runs on wall time, which a
frame-by-frame renderer does not have, so left alone it freezes on frame 0 or
lands somewhere different on every render. Pausing it and feeding it a negative
delay equal to the current time seeks it instead:

```tsx
animation: `hf-grain-noise ${cycle}s steps(1) infinite`,
animationDelay: `${-(frame / fps)}s`,
animationPlayState: "paused",
```

Frame-exact, deterministic, no intermediate file. This is the better path
whenever it is available — `grain-overlay` came across this way.

## 2. Rendered as a layer (`public/overlays/*.webm`)

Registry items that are canvas, GSAP or shader work cannot be hand-ported, and
should not be. They get built here, rendered with alpha, and composited by
Remotion — which keeps the timeline: when the card cuts away is a number in
`src/OltrepoTour/timeline.ts`, not something baked into the video.

`ink-bleed-reveal` came across this way, as the title card of `ValStafforaInk`.

### Rebuilding the overlay

Two things this environment needs that the CLI assumes:

```bash
# ffmpeg, from npm rather than apt (the CLI wants it on PATH)
npm i --no-save ffmpeg-static ffprobe-static
node -e 'const f=require("fs");f.mkdirSync("bin",{recursive:true});
  f.copyFileSync(require("ffmpeg-static"),"bin/ffmpeg");
  f.copyFileSync(require("ffprobe-static").path,"bin/ffprobe");
  f.chmodSync("bin/ffmpeg",0o755);f.chmodSync("bin/ffprobe",0o755)'
```

`bin/` is gitignored — 138MB of static binaries, recreated by the two lines
above. `vendor/gsap.min.js` is checked in on purpose: the scaffold loads GSAP
from jsdelivr, this environment's egress policy blocks it, and a composition
that needs the network at render time is one that fails somewhere else later.

Then:

```bash
cd hyperframes
PATH="$PWD/bin:$PATH" npx hyperframes@0.8.43 check
PATH="$PWD/bin:$PATH" npx hyperframes@0.8.43 render \
  --format png-sequence --output /tmp/inkseq
./bin/ffmpeg -y -framerate 30 -i /tmp/inkseq/frame_%06d.png \
  -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 32 -row-mt 1 -an \
  ../public/overlays/ink-title.webm
```

`--format webm` straight from the CLI came out `yuv420p` under this machine's
screenshot-capture path (BeginFrame needs chrome-headless-shell, which is not
here). The PNG sequence is RGBA regardless, so the alpha comes from encoding
that ourselves. It is also the frame-exact path, which is the one to want.

### What the host composition changes

`index.html` overrides two things in the registry component, both because it is
being used as a layer rather than as a finished frame:

- `.ibr-grain { display: none }` — it paints half-opacity paper grain across the
  whole frame, which over a map is a grey wash that drains everything under it.
  Remotion owns the grain on this film. Dropping it also took the render from
  204MB and 50s to 10MB and 8s.
- a cream `-webkit-text-stroke` on the mark, matching `src/shared/labelStyle.ts`,
  because the card lands on a map rather than on blank paper.

Neither is a fix to the component — both are what "layer, not frame" means.
