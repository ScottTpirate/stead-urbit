// Five additive T02/T09 cases on the existing synthetic interaction reference.
// Shared by the Firefox reference and the bounded remote Chromium renderer.
import assert from 'node:assert/strict';

async function focused(locator) {
  assert.equal(await locator.evaluate(element => element === document.activeElement), true);
}
async function contained(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true,
    'No horizontal page overflow');
}
async function iconMenu(page, report, label) {
  const trigger = page.getByRole('button', {name: 'More reference actions', exact: true});
  const measured = await trigger.evaluate(element => {
    const box = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return {width: box.width, height: box.height, color: style.color,
      background: getComputedStyle(element.closest('.reference-panel')).backgroundColor,
      coarse: matchMedia('(pointer: coarse)').matches, name: element.getAttribute('aria-label')};
  });
  const floor = measured.coarse ? 44 : 32;
  assert.ok(measured.width >= floor && measured.height >= floor, JSON.stringify(measured));
  function luminance(color) {
    const rgb = color.match(/[\d.]+/gu).slice(0, 3).map(Number).map(value => value / 255)
      .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
    return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
  }
  const first = luminance(measured.color), second = luminance(measured.background);
  measured.contrast = (Math.max(first, second) + .05) / (Math.min(first, second) + .05);
  assert.ok(measured.contrast >= 3, 'Icon contrast against its actual surface');
  report.overflow_targets ??= {}; report.overflow_targets[label] = measured;
  await trigger.focus(); await trigger.press('ArrowDown');
  const menu = page.getByRole('menu', {name: 'More reference actions', exact: true});
  const item = menu.getByRole('menuitem', {name: 'Inspect reference', exact: true});
  await item.waitFor(); await focused(item); await item.press('Enter');
  await menu.waitFor({state: 'hidden'}); await focused(trigger);
  await page.getByText('Inspect reference selected', {exact: true}).waitFor();
  await trigger.press('ArrowDown'); await item.waitFor(); await item.press('Escape');
  await menu.waitFor({state: 'hidden'}); await focused(trigger); await contained(page);
}

export const attachmentCases = [
  {name: 'attachments-read-only-read-preview-source-preserve-exact-markdown', async run(page) {
    const doc = page.getByRole('region', {name: 'Welcome to the project', exact: true});
    await page.getByRole('checkbox', {name: 'Read-only reference', exact: true}).check();
    assert.equal(await doc.getByRole('button', {name: 'Edit', exact: true}).count(), 0);
    await doc.locator('[data-attachment-state="link"]').waitFor();
    const link = doc.getByRole('link', {name: /^Open image\s*:\s*Document diagram\s*\(opens in a new tab\)$/u});
    assert.equal(await link.getAttribute('href'), 'https://attachments.example/document.svg');
    assert.equal(await link.getAttribute('target'), '_blank');
    assert.equal(await link.getAttribute('referrerpolicy'), 'no-referrer');
    assert.equal(await link.getAttribute('rel'), 'noopener noreferrer');
    await link.focus(); await focused(link);
    assert.equal(await doc.locator('img, iframe, object, embed').count(), 0);
    await doc.getByText('Image target unavailable.', {exact: true}).waitFor();
    const modes = doc.getByRole('group', {name: 'Document view', exact: true});
    await modes.getByRole('button', {name: 'Source', exact: true}).click();
    const source = doc.getByRole('textbox', {name: 'Markdown source', exact: true});
    const before = await source.inputValue(); assert.match(before, /!\[Document diagram\]\(https:\/\/attachments\.example\/document\.svg\)/u);
    assert.equal(await source.getAttribute('readonly'), '');
    await modes.getByRole('button', {name: 'Preview', exact: true}).click(); await link.waitFor();
    await modes.getByRole('button', {name: 'Read', exact: true}).click(); await link.waitFor();
    await modes.getByRole('button', {name: 'Source', exact: true}).click();
    assert.equal(await source.inputValue(), before);
    await modes.getByRole('button', {name: 'Read', exact: true}).click(); await link.waitFor();
  }},
  {name: 'repository-attachments-show-clone-unavailable-and-explicit-web-links', async run(page) {
    const repo = page.getByRole('region', {name: 'Repository attachments', exact: true});
    assert.equal(await repo.locator('[data-attachment-state="clone"]').count(), 3);
    assert.equal(await repo.locator('[data-attachment-state="unavailable"]').count(), 1);
    assert.equal(await repo.locator('[data-attachment-state="clone"] a, [data-attachment-state="unavailable"] a').count(), 0);
    assert.equal(await repo.locator('img, iframe, object, embed, a a').count(), 0);
    assert.equal(await repo.getByRole('link').count(), 2);
    const image = repo.getByRole('link', {name: /^Open image\s*:\s*External diagram\s*\(opens in a new tab\)$/u});
    assert.equal(await image.getAttribute('href'), 'https://attachments.example/repository.svg');
    await image.focus(); await focused(image); await image.press('Tab');
    const related = repo.getByRole('link', {name: 'Related link', exact: true});
    await focused(related); assert.equal(await related.getAttribute('href'), 'https://attachments.example/guide');
    assert.doesNotMatch(await repo.innerText(), /\(open\)/u);
  }},
  {name: 'long-attachment-descriptions-reflow-at-320-and-two-times-zoom', async run(page) {
    await page.getByRole('button', {name: /^Reference data:/u}).click();
    await page.getByRole('menuitemradio', {name: 'Crowded', exact: true}).click();
    await page.setViewportSize({width: 320, height: 1000});
    const repo = page.getByRole('region', {name: 'Repository attachments', exact: true});
    assert.ok((await repo.innerText()).includes('A deliberately long image description — 雪 🪴 '.repeat(15).trim()));
    await contained(page);
    for (const box of await repo.locator('.markdown-attachment').evaluateAll(items => items.map(item => ({
      width: item.getBoundingClientRect().width, parent: item.closest('article').getBoundingClientRect().width})))) {
      assert.ok(box.width <= box.parent + 1, JSON.stringify(box));
    }
    await page.setViewportSize({width: 1440, height: 1000});
    await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
    await contained(page);
    assert.equal(await repo.locator('img, iframe, object, embed').count(), 0);
    await page.evaluate(() => { document.documentElement.style.zoom = ''; });
    await page.setViewportSize({width: 320, height: 1000});
    await contained(page);
  }},
  {name: 'shared-icon-only-overflow-meets-desktop-target-and-keyboard-contract', async run(page, report) {
    await iconMenu(page, report, 'desktop1440');
  }},
  {name: 'shared-icon-only-overflow-meets-narrow-touch-target-and-focus-return',
    options: {viewport: {width: 320, height: 1000}, hasTouch: true},
    async run(page, report) { await iconMenu(page, report, 'narrow320Touch'); }},
];
