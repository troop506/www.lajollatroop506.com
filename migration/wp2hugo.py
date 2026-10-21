#!/usr/bin/env python3
"""Convert the WordPress site into this Hugo site.

    wp eval-file export.php > export.json      (inside the WordPress container)
    python3 wp2hugo.py export.json UPLOADS_DIR

UPLOADS_DIR is the WordPress wp-content/uploads directory. Writes content/,
data/menu.yaml and copies every upload the content refers to into uploads/.
Block markup that has no Markdown equivalent becomes a shortcode (image,
columns/column, embed) or, as a last resort, raw HTML; those are listed at
the end so they can be checked.
"""
import json
import re
import shutil
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
HOST = re.compile(r'https?://(?:www\.)?lajollatroop506\.com|https?://wp\d*\.do\.cnshost\.net|https?://troop506\.websites\.localhost(?::\d+)?')
# E-commerce pages, plus the private posts page and an unused draft.
DROP_PAGES = {'shop', 'cart', 'checkout', 'my-account', 'apparel', 'refund_returns', 'news'}
DROP_MENU = {'506 Store', 'Shop', 'My account', 'Checkout', 'Cart'}

uploads = set()      # /wp-content/uploads/... paths referenced by the content
raw_blocks = []      # (page, snippet) kept as raw HTML


def fix_url(url):
    url = HOST.sub('', url.strip()) or '/'
    if url.startswith('/wp-content/uploads/'):
        url = url.split('?')[0]
        uploads.add(url)
    return url


def esc_text(s):
    s = re.sub(r'[ \t\r\n]+', ' ', s)  # not \s: keep non-breaking spaces
    s = s.replace('\\', '\\\\')
    for ch in '*_`[]':
        s = s.replace(ch, '\\' + ch)
    return s.replace('<', '&lt;')


def attr(v):
    return str(v).replace('"', '&quot;')


def raw(node, where):
    """Keep a node as HTML, with URLs fixed and no blank lines inside."""
    for t in node.find_all(True):
        for a in ('href', 'src'):
            if t.get(a):
                t[a] = fix_url(t[a])
        if t.get('srcset'):
            del t['srcset']
            t.attrs.pop('sizes', None)
    html = re.sub(r'\n\s*\n', '\n', str(node)).strip()
    raw_blocks.append((where, html[:90]))
    return html


# --- inline ---------------------------------------------------------------

def inline(node, where):
    out = []
    for c in node.children:
        if isinstance(c, NavigableString):
            out.append(esc_text(str(c)))
        elif c.name == 'br':
            out.append('\n')
        elif c.name == 'a' and c.get('href'):
            text = inline(c, where).strip()
            if text:
                out.append(f'[{text}]({fix_url(c["href"])})')
        elif c.name in ('strong', 'b', 'em', 'i'):
            mark = '**' if c.name in ('strong', 'b') else '_'
            text = inline(c, where)
            if text.strip():
                lead = text[:len(text) - len(text.lstrip())]
                trail = text[len(text.rstrip()):]
                out.append(f'{lead}{mark}{text.strip()}{mark}{trail}')
            else:
                out.append(text)
        elif c.name == 'code':
            out.append(f'`{c.get_text()}`')
        else:
            out.append(raw(c, where))
    return ''.join(out)


def has_extra_attrs(tag, allowed=('wp-block-heading', 'wp-block-list')):
    classes = [c for c in tag.get('class', []) if c not in allowed]
    return bool(classes or tag.get('style') or tag.get('id'))


# --- blocks ---------------------------------------------------------------

def md_list(lst, where, depth=0):
    lines = []
    n = int(lst.get('start', 1))
    for li in lst.find_all('li', recursive=False):
        nested = [c for c in li.children if isinstance(c, Tag) and c.name in ('ul', 'ol')]
        for c in nested:
            c.extract()
        marker = f'{n}.' if lst.name == 'ol' else '-'
        n += 1
        text = inline(li, where).strip().replace('\n', '\n' + ' ' * (depth + 1) * 4)
        lines.append(' ' * depth * 4 + f'{marker} {text}')
        for c in nested:
            lines.append(md_list(c, where, depth + 1))
    return '\n'.join(lines)


def image(node, shortcode=False):
    """A core or Spectra (uagb) image block -> image shortcode or Markdown."""
    img = node.find('img')
    classes = set(node.get('class', [])) | set(img.find_parent('figure').get('class', []) if img.find_parent('figure') else [])
    uagb = any(c.startswith('wp-block-uagb-image') for c in node.get('class', []))
    align = next((c[5:] for c in classes if c in ('aligncenter', 'alignleft', 'alignright')), '')
    if uagb:
        align = next((c.split('--align-')[1] for c in node.get('class', []) if '--align-' in c), 'none')
        align = '' if align == 'none' else align
    size = next((c[5:] for c in classes if c.startswith('size-')), '')
    resized = ''
    m = re.search(r'width:\s*(\d+)px', img.get('style', ''))
    if m:
        resized = m.group(1)
    cap = node.find('figcaption')
    caption = inline(cap, 'caption').strip() if cap else ''
    link = img.find_parent('a')
    # Same attribute order as the Photo block in static/admin/index.html.
    p = {
        'src': fix_url(img['src']),
        'alt': img.get('alt', ''),
        'caption': caption,
        'align': align,
        'resized': resized,
        'size': size if size not in ('', 'large') else '',
        'link': fix_url(link['href']) if link and link.get('href') else '',
        'width': img.get('width', ''),
        'height': img.get('height', ''),
        'kind': 'uagb' if uagb else '',
        # Older WordPress markup: <div class="wp-block-image"><figure class="alignX ...">
        'wrapper': ('default' if 'is-style-default' in node.get('class', []) else 'plain') if node.name == 'div' and 'wp-block-image' in node.get('class', []) else '',
        # Spectra keeps per-image CSS under this class (wp-after.css).
        'block': next((c[len('uagb-block-'):] for c in node.get('class', []) if c.startswith('uagb-block-')), ''),
    }
    if not shortcode and not any(p[k] for k in ('align', 'size', 'resized', 'caption', 'link', 'kind', 'wrapper')):
        return f'![{esc_text(p["alt"])}]({p["src"]})'
    args = ' '.join(f'{k}="{attr(v)}"' for k, v in p.items() if v)
    return '{{< image ' + args + ' >}}'


def is_image(node):
    cls = node.get('class', [])
    return bool(node.find('img')) and ('wp-block-image' in cls or any(x.startswith('wp-block-uagb-image') for x in cls))


def photo_row(columns):
    """Columns that each hold just one image, with no custom widths."""
    cols = columns.find_all('div', class_='wp-block-column', recursive=False)
    for col in cols:
        kids = [x for x in col.children if isinstance(x, Tag) or str(x).strip()]
        if len(kids) != 1 or not isinstance(kids[0], Tag) or not is_image(kids[0]) or col.get('style'):
            return False
    return bool(cols)


def blocks(container, where):
    out = []
    for c in container.children:
        if isinstance(c, NavigableString):
            if c.strip():
                out.append(esc_text(c.strip()))
            continue
        cls = set(c.get('class', []))
        if c.name == 'p':
            if has_extra_attrs(c) or not c.get_text(strip=True) and not c.find('img'):
                out.append(raw(c, where))
            elif c.find('img') and not c.get_text(strip=True):
                out.append(raw(c, where))
            else:
                out.append(inline(c, where).strip())
        elif re.fullmatch(r'h[1-6]', c.name):
            if has_extra_attrs(c):
                out.append(raw(c, where))
            else:
                out.append('#' * int(c.name[1]) + ' ' + inline(c, where).strip())
        elif c.name in ('ul', 'ol') and not has_extra_attrs(c):
            out.append(md_list(c, where))
        elif c.find('img') and ('wp-block-image' in cls or any(x.startswith('wp-block-uagb-image') for x in cls)):
            out.append(image(c))
        elif 'wp-block-columns' in cls and photo_row(c):
            imgs = [image(next(x for x in col.children if isinstance(x, Tag)), shortcode=True)
                    for col in c.find_all('div', class_='wp-block-column', recursive=False)]
            out.append('\n'.join(['{{< photo-row >}}', *imgs, '{{< /photo-row >}}']))
        elif 'wp-block-columns' in cls:
            parts = ['{{% columns %}}']
            for col in c.find_all('div', class_='wp-block-column', recursive=False):
                m = re.search(r'flex-basis:\s*([\d.]+%)', col.get('style', ''))
                parts.append('{{% column' + (f' width="{m.group(1)}"' if m else '') + ' %}}')
                parts.append(blocks(col, where))
                parts.append('{{% /column %}}')
            parts.append('{{% /columns %}}')
            out.append('\n\n'.join(parts))
        elif 'wp-block-embed' in cls and c.find('iframe'):
            url = c.find('iframe')['src']
            t = c.find('iframe').get('title', '')
            out.append(f'{{{{< embed url="{attr(url)}"' + (f' title="{attr(t)}"' if t else '') + ' >}}')
        elif 'wp-block-group' in cls:
            inner = c.find(class_='wp-block-group__inner-container') or c
            out.append(blocks(inner, where))
        else:
            out.append(raw(c, where))
    return '\n\n'.join(b for b in out if b.strip())


def convert(html, where):
    soup = BeautifulSoup(html, 'html.parser')
    return blocks(soup, where).strip() + '\n'


# --- pages ----------------------------------------------------------------

def write(path, front, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=1000)
    path.write_text(f'---\n{fm}---\n\n{body}')


def title(s):
    return BeautifulSoup(s, 'html.parser').get_text()


def home(item):
    """The home page: Kadence slider + intro row, body text, latest posts."""
    soup = BeautifulSoup(item['content'], 'html.parser')
    row = soup.find(class_='wp-block-kadence-rowlayout')
    slides = []
    for li in row.select('.kb-gallery-slide-item'):
        img = li.find('img')
        cap = li.find('figcaption')
        slides.append({
            'image': fix_url(img.get('data-full-image') or img['src']),
            'alt': img.get('alt', ''),
            'caption': cap.get_text(strip=True) if cap else '',
        })
    intro = row.select('.wp-block-kadence-column')[1].find(class_='kt-inside-inner-col')
    posts = soup.find(class_='wp-block-kadence-posts')
    before = []
    for sib in row.find_next_siblings():
        if sib is posts or sib.find(class_='wp-block-kadence-posts'):
            break
        before.append(sib)
    body = BeautifulSoup('', 'html.parser')
    for b in before:
        body.append(b)
    front = {
        'title': title(item['title']),
        'slider': slides,
        'intro': convert(str(intro.decode_contents()), 'home intro'),
        'latest_posts': 6,
    }
    write(ROOT / 'content/_index.md', front, convert(str(body), 'home'))


def main(export, uploads_dir):
    d = json.load(open(export))
    terms = {(t['taxonomy'], t['slug']): t for t in d['terms']}
    for item in d['items']:
        where = item['slug'] or item['id']
        if item['type'] == 'page':
            if item['slug'] in DROP_PAGES:
                continue
            if item['slug'] == 'home':
                home(item)
                continue
            front = {'title': title(item['title']), 'url': item['path'], 'date': item['date'].replace(' ', 'T')}
            if item['template'] == 'pagetemplate-widepage.php':
                front['layout'] = 'wide'
            if item['status'] != 'publish':
                front['draft'] = True
                front.pop('url')
            write(ROOT / f'content/pages/{item["slug"] or item["id"]}.md', front, convert(item['content'], where))
        else:
            front = {
                'title': title(item['title']),
                'date': item['date'].replace(' ', 'T'),
                'author': item['author'],
                'categories': item['categories'],
                'tags': item['tags'],
            }
            if item['thumbnail']:
                front['image'] = fix_url(item['thumbnail'])
                if item['thumb_alt']:
                    front['image_alt'] = item['thumb_alt']
            if item['status'] != 'publish':
                front['draft'] = True
            if not front['tags']:
                del front['tags']
            slug = item['slug'] or re.sub(r'[^a-z0-9]+', '-', front['title'].lower()).strip('-')
            write(ROOT / f'content/posts/{slug}.md', front, convert(item['content'], where))

    # Taxonomy term pages carry the WordPress display names.
    for (tax, slug), t in terms.items():
        section = 'categories' if tax == 'category' else 'tags'
        if t['count']:
            write(ROOT / f'content/{section}/{slug}/_index.md', {'title': title(t['name']), 'slug': slug}, '')

    # Header menu, without the store.
    items = {m['id']: dict(m, children=[]) for m in d['menu'] if title(m['title']) not in DROP_MENU}
    tree = []
    for m in sorted(items.values(), key=lambda m: m['order']):
        node = {'title': title(m['title']), 'url': m['url']}
        m['node'] = node
    for m in sorted(items.values(), key=lambda m: m['order']):
        parent = items.get(m['parent'])
        if m['parent'] and parent:
            parent['node'].setdefault('children', []).append(m['node'])
        elif not m['parent']:
            tree.append(m['node'])
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'data/menu.yaml').write_text(yaml.safe_dump({'items': tree}, sort_keys=False, allow_unicode=True))

    # Copy the uploads the content refers to.
    missing = []
    for u in sorted(uploads):
        src = Path(uploads_dir) / u[len('/wp-content/uploads/'):]
        dst = ROOT / 'uploads' / u[len('/wp-content/uploads/'):]
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            missing.append(u)

    print(f'{len(uploads)} uploads referenced, {len(missing)} missing:', *missing, sep='\n  ')
    print(f'{len(raw_blocks)} raw HTML blocks:')
    for where, snippet in raw_blocks:
        print(f'  {where}: {snippet}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
