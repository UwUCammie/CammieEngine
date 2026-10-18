'use strict';
const root = '/cammie-engine/';
const button = document.querySelector('#theme-toggle');
function theme(value) {
  document.documentElement.dataset.theme = value;
  document.querySelector('meta[name="theme-color"]').content = value === 'dark' ? '#17121e' : '#faf8fc';
  button.textContent = value === 'dark' ? 'Light mode' : 'Dark mode';
  button.setAttribute('aria-label', 'Switch to ' + (value === 'dark' ? 'light' : 'dark') + ' mode');
}
let preferred;
try { preferred = localStorage.getItem('theme'); } catch {}
theme(['dark', 'light'].includes(preferred) ? preferred : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
button.addEventListener('click', () => {
  const value = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  theme(value);
  try { localStorage.setItem('theme', value); } catch {}
});
const onChangelog = location.pathname === root + 'changelog/';
if (onChangelog) {
  document.querySelector('.hero').hidden = true;
  document.querySelector('.engine-overview').hidden = true;
  document.querySelector('#changelog').hidden = false;
  document.title = 'Cammie Engine changelog / uwucammie';
}
async function load() {
  const response = await fetch(root + 'latest.json', {cache: 'no-store'});
  if (!response.ok) throw new Error('Release information is temporarily unavailable. Please try again shortly.');
  const release = await response.json();
  document.querySelector('#release-version').textContent = release.tag + ' alpha / Windows x64';
  document.querySelector('#download-detail').textContent = Math.round(release.archive.size / 1048576) + ' MB portable ZIP. Extract it to a writable folder and run Funkin.exe.';
  // Derive public links from the validated tag, never render HTML from release notes.
  if (!/^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(release.tag)) throw new Error('Invalid release information.');
  const base = root + 'releases/' + release.tag + '/';
  document.querySelector('#download').href = base + 'CammieEngine-' + release.tag + '-windows-x64.zip';
  const checksum = document.querySelector('#checksum');
  checksum.href = base + 'SHA256SUMS.txt';
  checksum.hidden = false;
  if (onChangelog) {
    const notesResponse = await fetch(base + 'changelog.txt');
    if (!notesResponse.ok) throw new Error('The changelog could not be loaded. Please try again shortly.');
    const notes = await notesResponse.text();
    const container = document.querySelector('#release-notes');
    container.replaceChildren();
    for (const section of notes.split(/(?=^v\d+\.\d+\.\d+[^\n]*$)/m)) {
      const lines = section.trim().split('\n');
      if (!/^v\d+\./.test(lines[0])) continue;
      const article = document.createElement('article');
      article.className = 'release-note';
      const heading = document.createElement('h3');
      heading.textContent = lines.shift();
      const body = document.createElement('p');
      body.textContent = lines.join('\n').trim();
      article.append(heading, body);
      container.append(article);
    }
  }
}
load().catch(error => {
  document.querySelector(onChangelog ? '#release-notes' : '#release-version').textContent = error.message;
});
