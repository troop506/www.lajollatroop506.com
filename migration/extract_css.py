#!/usr/bin/env python3
"""Collect the inline <style> blocks WordPress printed into two stylesheets.

    python3 extract_css.py SAVED_HTML_DIR

SAVED_HTML_DIR holds pages saved from the running WordPress site. Writes
static/wp-content/css/wp-before.css (loaded before the theme's style.css, as
WordPress did) and wp-after.css (loaded after it), plus home.css for the
Kadence blocks only the home page uses and uagb-blocks.css for Spectra image
blocks (see head.html for where each loads).
"""
import collections
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
BEFORE = ['wp-img-auto-sizes-contain-inline-css', 'wp-emoji-styles-inline-css', 'wp-block-library-inline-css',
          'wp-block-heading-inline-css', 'wp-block-list-inline-css', 'wp-block-image-inline-css',
          'wp-block-columns-inline-css', 'wp-block-paragraph-inline-css', 'wp-block-embed-inline-css',
          'wp-block-group-inline-css', 'wp-block-separator-inline-css', 'wp-block-button-inline-css',
          'classic-theme-styles-inline-css', 'global-styles-inline-css']
AFTER = ['kadence-blocks-global-variables-inline-css', 'kadence_blocks_palette_css', None,
         'uagb-style-conditional-extension']
HOME = ['kadence_blocks_css-inline-css']


def main(saved):
    seen = collections.defaultdict(collections.Counter)
    for f in Path(saved).glob('*.html'):
        for t in BeautifulSoup(f.read_text(), 'html.parser').find_all('style'):
            if t.find_parent('head'):
                seen[t.get('id')][t.string or ''] += 1
    common = lambda key: seen[key].most_common(1)[0][0] if seen[key] else ''
    union = lambda pred: '\n'.join(s for k in sorted(seen, key=str) if pred(k) for s in seen[k])

    out = ROOT / 'static/wp-content/css'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'wp-before.css').write_text('\n'.join(f'/* {k} */\n{common(k)}' for k in BEFORE) + '\n')
    after = [f'/* {k} */\n{common(k)}' for k in AFTER]
    after.append('/* core-block-supports-inline-css */\n' + union(lambda k: k == 'core-block-supports-inline-css'))
    (out / 'wp-after.css').write_text('\n'.join(after) + '\n')
    # Spectra block CSS; head.html loads it where WordPress did.
    (out / 'uagb-blocks.css').write_text(union(lambda k: str(k).startswith('uagb-style-frontend-')) + '\n')
    (out / 'home.css').write_text('\n'.join(common(k) for k in HOME) + '\n')
    print('ids seen:', sorted(map(str, seen)))


if __name__ == '__main__':
    main(sys.argv[1])
