// Builds the Pages site: every demo through `interactive-demo build`, then the
// SUSE start page and the SUSE branding of each demo page.
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const dist = join(root, 'dist');
const catalog = JSON.parse(readFileSync(join(root, 'catalog.json'), 'utf8'));

const built = catalog.demos.filter((d) => existsSync(join(root, 'demos', d.slug, 'demo.config.json')));

if (existsSync(dist) && !existsSync(join(dist, '.interactive-demo-build'))) rmSync(dist, { recursive: true });
execFileSync('npx', ['interactive-demo', 'build', '--out', 'dist'], { cwd: root, stdio: ['ignore', 'ignore', 'inherit'] });

cpSync(join(root, 'brand'), join(dist, 'brand'), { recursive: true });
cpSync(join(root, 'site', 'hub.css'), join(dist, 'hub.css'));

const escape = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// The first screen of a demo is its card's picture.
function thumb(slug) {
  const config = JSON.parse(readFileSync(join(root, 'demos', slug, 'demo.config.json'), 'utf8'));
  const step = config.steps.find((s) => s.kind === 'content');
  if (!step) return null;
  const bg = step.background;
  return bg.type === 'video' ? bg.posterSrc : bg.src;
}

// Each demo page: SUSE stylesheet, SUSE | NVIDIA logos back to the start page,
// "All demos" back to the start page wherever the site is hosted.
const brandLogos =
  '<a href="../" class="demo-page-btn suse-brand-logos" aria-label="All demos">' +
  '<img src="../brand/suse-logo-light.png" alt="SUSE" /><span class="suse-brand-sep" aria-hidden="true"></span>' +
  '<img src="../brand/nvidia-logo-light.png" alt="NVIDIA" /></a>';

for (const d of built) {
  const page = join(dist, d.slug, 'index.html');
  let html = readFileSync(page, 'utf8');
  html = html.replace(
    '</head>',
    '    <link rel="stylesheet" href="../brand/suse.css" />\n    <link rel="stylesheet" href="../brand/suse-page.css" />\n    <link rel="icon" href="../brand/suse-logo-light.png" />\n  </head>',
  );
  html = html.replace(/<a href="[^"]*" class="demo-page-btn demo-page-brand"[^>]*>.*?<\/a>/, brandLogos);
  html = html.split(`href="${catalog.site}"`).join('href="../"');
  html = html.replace(/(<a [^>]*href="\.\.\/"[^>]*) target="_blank"/g, '$1');
  html = html.replace(/(<a [^>]*href="\.\.\/"[^>]*) rel="[^"]*"/g, '$1');
  writeFileSync(page, html);
}

function card(d, featured = false) {
  const ready = built.includes(d);
  const src = ready ? thumb(d.slug) : null;
  const picture = src
    ? `<img src="./${d.slug}/${escape(src)}" alt="" loading="lazy" />`
    : '<span class="placeholder">COMING SOON</span>';
  const chips = d.chapters
    .map((c) => `<span class="chip${c === 'SUSE Security' ? ' security' : ''}">${escape(c)}</span>`)
    .join('');
  const tagName = ready ? 'a' : 'div';
  const href = ready ? ` href="./${d.slug}/"` : '';
  return `<${tagName} class="card${featured ? ' featured' : ''}${ready ? '' : ' soon'}"${href}>
        <div class="thumb">${picture}</div>
        <div class="body">
          <span class="tag">${escape(d.tag)}</span>
          <h3>${escape(d.title)}</h3>
          <p>${escape(d.pitch)}</p>
          <div class="chips">${chips}</div>
          <span class="action">${ready ? 'Start the demo' : 'Coming soon'}</span>
        </div>
      </${tagName}>`;
}

const featured = catalog.demos.filter((d) => d.featured);
const rest = catalog.demos.filter((d) => !d.featured);
const hub = readFileSync(join(root, 'site', 'index.html'), 'utf8')
  .replace('{{FEATURED}}', featured.map((d) => card(d, true)).join('\n      '))
  .replace('{{CARDS}}', rest.map((d) => card(d)).join('\n        '));
writeFileSync(join(dist, 'index.html'), hub);
writeFileSync(join(dist, '.nojekyll'), '');

console.log(`site: ${built.length}/${catalog.demos.length} demos built into dist/`);
