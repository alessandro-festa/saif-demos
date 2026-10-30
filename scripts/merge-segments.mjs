// Joins the captured segments of one demo into demos/<slug>/ following its
// story (stories/<slug>.json): intro cover, one cover + the captured steps per
// chapter, closing cover with "Back to all demos".
//
//   node scripts/merge-segments.mjs <slug>
//
// Segments are what `interactive-demo capture stop --out recordings/<slug>/<segment>`
// wrote. The copy lives in the story, so a segment can be re-recorded and
// re-merged without losing it.
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { basename, join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const slug = process.argv[2];
if (!slug) {
  console.error('usage: node scripts/merge-segments.mjs <slug>');
  process.exit(1);
}

const storyPath = join(root, 'stories', `${slug}.json`);
const story = JSON.parse(readFileSync(storyPath, 'utf8'));

// The published URL is keyed on the id: mint it once, keep it in the story.
if (!/^[A-Za-z0-9_-]{12}$/.test(story.id ?? '')) {
  story.id = randomBytes(9).toString('base64url');
  writeFileSync(storyPath, JSON.stringify(story, null, 2) + '\n');
}

const PINE = '#0C322C';
const MIDNIGHT = '#192072';
const JUNGLE = '#30BA78';
const coverBackground = { type: 'color', from: PINE, to: MIDNIGHT };

const out = join(root, 'demos', slug);
rmSync(out, { recursive: true, force: true });
mkdirSync(join(out, 'assets'), { recursive: true });
for (const logo of ['suse-logo-light.png', 'nvidia-logo-light.png']) {
  copyFileSync(join(root, 'brand', logo), join(out, 'assets', logo));
}

// capture stop --out <dir> writes <dir>/<captured-slug>/demo.config.json
function segmentDir(segment) {
  const dir = join(root, 'recordings', slug, segment);
  if (existsSync(join(dir, 'demo.config.json'))) return dir;
  const sub = existsSync(dir) ? readdirSync(dir).find((d) => existsSync(join(dir, d, 'demo.config.json'))) : null;
  if (!sub) throw new Error(`no capture for segment "${segment}" in ${dir}`);
  return join(dir, sub);
}

function cover(id, { title, description, cta, secondaryCta }) {
  return {
    kind: 'cover',
    id,
    widgets: [
      {
        type: 'headline',
        id: `${id}-h`,
        logo: { src: 'assets/suse-logo-light.png', alt: 'SUSE', height: 48 },
        title,
        titleColor: '#FFFFFF',
        description,
        descriptionColor: '#E6F7EF',
        textAlign: 'middle',
        cta: { background: JUNGLE, textColor: PINE, animation: 'none', ...cta },
        ...(secondaryCta ? { secondaryCta: { background: '#FFFFFF1F', textColor: '#FFFFFF', animation: 'none', ...secondaryCta } } : {}),
      },
    ],
    background: coverBackground,
    advance: { trigger: 'click' },
  };
}

const steps = [];
const chapters = [];

steps.push(
  cover('intro', {
    title: story.title,
    description: story.intro,
    cta: { label: 'Start', action: { type: 'next' } },
    secondaryCta: { label: 'All demos', action: { type: 'url', href: '../', target: '_self' } },
  }),
);

for (const chapter of story.chapters) {
  const ids = [];
  const coverId = `${chapter.id}-cover`;
  steps.push(cover(coverId, { title: chapter.title, description: chapter.blurb, cta: { label: 'Continue', action: { type: 'next' } } }));
  ids.push(coverId);

  for (const segment of chapter.segments) {
    const dir = segmentDir(segment.name);
    const captured = JSON.parse(readFileSync(join(dir, 'demo.config.json'), 'utf8'));
    const edits = segment.steps ?? {};
    captured.steps.forEach((step, i) => {
      const n = String(i + 1);
      const edit = edits[n] ?? {};
      if (edit.drop || (segment.keep && !segment.keep.includes(i + 1))) return;
      const id = `${segment.name}-${n}`;
      const s = structuredClone(step);
      s.id = id;
      if (edit.label) s.label = edit.label;

      // Media: prefix with the segment so names never clash.
      for (const key of ['src', 'posterSrc']) {
        const src = s.background?.[key];
        if (!src || /^(https?:|data:|blob:|\/)/.test(src)) continue;
        const name = `${segment.name}-${basename(src)}`;
        copyFileSync(join(dir, src), join(out, 'assets', name));
        s.background[key] = `assets/${name}`;
      }

      if (edit.zoom === false) delete s.transform;
      else if (edit.zoom) s.transform = edit.zoom;

      const message = (s.annotations ?? []).find((a) => a.type === 'message');
      if (message) {
        if (edit.text) message.text = edit.text;
        if (edit.x !== undefined) message.x = edit.x;
        if (edit.y !== undefined) message.y = edit.y;
        if (edit.variant) message.variant = edit.variant;
        if (edit.anchor) message.anchor = edit.anchor;
      }
      for (const [k, b] of (edit.blur ?? []).entries()) {
        s.annotations = [...(s.annotations ?? []), { id: `${id}-blur-${k}`, type: 'blur', intensity: 12, ...b }];
      }
      steps.push(s);
      ids.push(id);
    });
  }
  chapters.push({ id: chapter.id, title: chapter.title, stepIds: ids });
}

steps.push(
  cover('outro', {
    title: story.outro.title,
    description: story.outro.description,
    cta: { label: 'Back to all demos', action: { type: 'url', href: story.outro.href ?? '../', target: '_self' } },
    secondaryCta: { label: 'Replay', action: { type: 'restart' } },
  }),
);

const config = {
  $schema: 'https://cdn.jsdelivr.net/npm/@inkly-org/interactive-demo/dist/schema/demo.config.json',
  id: story.id,
  version: 1,
  title: story.title,
  subtitle: story.subtitle,
  background: { type: 'color', from: PINE, to: MIDNIGHT },
  theme: { brand: { logo: 'assets/suse-logo-light.png', name: 'SUSE AI Factory with NVIDIA' } },
  chrome: { controls: 'full', autoplay: false, branding: false },
  chapters,
  steps,
};
writeFileSync(join(out, 'demo.config.json'), JSON.stringify(config, null, 2) + '\n');
console.log(`demos/${slug}: ${steps.length} steps in ${chapters.length} chapters`);
