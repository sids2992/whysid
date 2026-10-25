#!/usr/bin/env python3
"""Builds whysid.com from posts/*.md and site.md into site/.

Standard library only, plus Pillow for the share-card images.
Run:  python3 build.py
"""
import html
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "posts"
FONTS = ROOT / "fonts"
OUT = ROOT / "site"

# ---------------------------------------------------------------- parsing


def read_front_matter(text):
    """Split '---\\nkey: value\\n---\\nbody' into (dict, body)."""
    meta, body = {}, text
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        current = None
        for line in fm.splitlines():
            if not line.strip():
                continue
            if line.startswith("  ") and current:
                k, _, v = line.strip().partition(":")
                meta[current][k.strip()] = v.strip()
            else:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if v == "":
                    meta[k] = {}
                    current = k
                else:
                    meta[k] = v
                    current = None
    return meta, body.strip()


def smart(t):
    """Curly quotes and apostrophes, leaving link URLs untouched."""
    parts = re.split(r"(\]\(https?://[^\s)]+\))", t)
    for i in range(0, len(parts), 2):
        p = parts[i]
        p = re.sub(r"(?<=\w)'", "\u2019", p)
        p = re.sub(r"'(?=\w)", "\u2018", p)
        p = p.replace("'", "\u2019")
        p = re.sub(r'(^|[\s(\[])"', "\\1\u201c", p)
        p = p.replace('"', "\u201d")
        parts[i] = p
    return "".join(parts)


def inline(md):
    """Escape HTML, then turn [text](url), **bold** and *italic* into tags."""
    s = html.escape(smart(md), quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    return s


def strip_md(md):
    s = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r"\1", md)
    return s.replace("**", "").replace("*", "")


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "post"


def first_sentence(text, limit=140):
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def load_site():
    meta, intro = read_front_matter((ROOT / "site.md").read_text(encoding="utf-8"))
    meta.setdefault("socials", {})
    meta["domain"] = meta.get("domain", "").rstrip("/")
    def intro_line(l):
        m = re.match(r"Built an? (\w)(.*)$", l)
        if not m:
            return f"<p>{inline(l)}</p>"
        short = m.group(1).upper() + m.group(2)
        return f'<p><span class="full">{inline(l)}</span><span class="short">{inline(short)}</span></p>'
    meta["intro_html"] = '<div class="intro">' + "".join(intro_line(l.strip()) for l in intro.splitlines() if l.strip()) + "</div>"
    return meta


def load_posts():
    posts = []
    for path in sorted(POSTS.glob("*.md")):
        meta, body = read_front_matter(path.read_text(encoding="utf-8"))
        if "title" not in meta or "date" not in meta:
            sys.exit(f"{path.name}: needs 'title' and 'date' in the front matter")
        paras, question = [], None
        for block in re.split(r"\n\s*\n", body):
            block = block.strip()
            if not block:
                continue
            if block.startswith("?"):
                question = block.lstrip("? ").strip()
            else:
                paras.append(block)
        plain = " ".join(strip_md(p) for p in paras)
        post = {
            "title": smart(meta["title"].strip()),
            "date": datetime.strptime(meta["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc),
            "slug": meta.get("slug") or slugify(meta["title"]),
            "paras_html": [inline(p) for p in paras],
            "plain": plain,
            "first": first_sentence(plain) if plain else "",
            "question": question,
            "picture": None,
            "alt": meta.get("alt", "").strip(),
            "words": len(plain.split()),
        }
        if meta.get("picture"):
            pic = path.parent / meta["picture"].strip()
            if not pic.exists():
                sys.exit(f"{path.name}: picture {pic.name} not found next to the post")
            if not post["alt"]:
                sys.exit(f"{path.name}: a post with a picture needs an 'alt' line")
            post["picture"] = pic
        posts.append(post)
    posts.sort(key=lambda p: p["date"], reverse=True)
    slugs = [p["slug"] for p in posts]
    if len(slugs) != len(set(slugs)):
        sys.exit("two posts share a slug; add a 'slug:' line to one of them")
    return posts


# ---------------------------------------------------------------- html

CSS = """
@font-face{font-family:A;src:url(/fonts/a.woff2) format("woff2");font-weight:200 800;font-style:normal;font-display:swap}
:root{--bg:#f7f5f0;--fg:#1c1b19;--mute:#6b6761;--line:#cbc6bd;--accent:#b8401f;--w:360;--s:15px;color-scheme:light dark}
@media(prefers-color-scheme:dark){:root{--bg:#151412;--fg:#dcd8cf;--mute:#a39e95;--line:#4b4842;--accent:#e8734d;--w:340}}
*{box-sizing:border-box}
html{background:var(--bg);color:var(--fg);font:400 20px/1.6 A,"Helvetica Neue",Arial,sans-serif;font-variation-settings:"wght" var(--w);font-weight:var(--w);-webkit-text-size-adjust:100%;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
body{margin:0;padding:64px 24px 56px;max-width:688px;margin-inline:auto;animation:in .15s ease-out}
@keyframes in{from{opacity:0}to{opacity:1}}
@media(prefers-reduced-motion:reduce){body{animation:none}}
p,h1{margin:0}
a{color:inherit;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:4px;text-decoration-color:var(--line);transition:text-decoration-color .15s,color .15s}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:2px}
::selection{background:var(--accent);color:var(--bg)}
h1,.t,.list span{text-wrap:balance}p{text-wrap:pretty}
time{font-variant-numeric:tabular-nums}
a:hover{text-decoration-color:currentColor}
.t{font-size:var(--s);line-height:1.4;color:var(--mute);margin-bottom:16px}
.t time{white-space:nowrap;font-size:.93em}
.pic{display:block;width:100%;height:auto;aspect-ratio:4/3;object-fit:cover;border-radius:4px;margin-bottom:24px}
.body p+p{margin-top:1em}
.share{margin-top:32px;font-size:var(--s);line-height:1.5}
.share a{color:var(--accent);text-decoration-color:currentColor}
.id{margin-top:56px;font-size:var(--s);line-height:1.4;color:var(--mute)}
.id a{text-decoration:none}.id a:hover{text-decoration:underline}
.nav{margin-top:8px;font-size:var(--s);line-height:1.4;color:var(--mute);display:flex;gap:16px}
h1{font-size:28px;line-height:1.2;font-weight:600;font-variation-settings:"wght" 600;margin-bottom:16px}
h1 .dot{color:var(--accent);display:inline-block}
h1.blink .dot{animation:blink 1.2s ease-in-out .6s 1,breathe 5s ease-in-out 2.4s 4}
h1.still .dot{animation:none}
@keyframes blink{0%,100%{opacity:1}18%{opacity:.12}36%{opacity:1}54%{opacity:.12}72%{opacity:1}}
@keyframes breathe{0%,100%{opacity:1}50%{opacity:.45}}
@media(prefers-reduced-motion:reduce){h1.blink .dot{animation:none}}
.intro p+p{font-size:var(--s);line-height:1.5;color:var(--mute)}
.intro .short{display:none}
@media(max-width:395px){.intro .full{display:none}.intro .short{display:inline}}.intro p:nth-child(2){margin-top:16px}.intro p+p+p{margin-top:8px}
.soc{margin:32px 0 40px;font-size:var(--s);line-height:1.5;color:var(--mute);display:flex;gap:20px;flex-wrap:wrap}
.soc a.ok{color:var(--accent);text-decoration:none}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.list{display:flex;flex-direction:column}
.list a{display:flex;align-items:baseline;gap:16px;min-height:44px;padding:8px 0;text-decoration:none}
.list a span{line-height:1.4;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:4px;text-decoration-color:var(--line)}
.list a:hover span{text-decoration-color:currentColor}
.list a time{flex:none;width:6.6em;font-size:calc(var(--s) * .93);line-height:1.4;color:var(--mute);white-space:nowrap}
@media(min-width:700px){:root{--s:clamp(16px,.25vw + 13px,18px)}html{font-size:clamp(21px,.45vw + 15.5px,23px);line-height:1.65}body{max-width:calc(30.5em + 48px);padding:112px 24px 96px}h1{font-size:clamp(32px,1.2vw + 17px,40px)}.soc{gap:24px}.nav{gap:20px}.intro p+p+p{margin-top:4px}}
@media print{:root{--bg:#fff;--fg:#000;--mute:#555;--line:#999}body{padding:0;max-width:none;animation:none}.share,.nav{display:none}.body a::after{content:" (" attr(href) ")";font-size:.8em;color:#555}.pic{max-width:60%}}
"""

COPY_JS = """<span class="sr" aria-live="polite"></span>
<script>document.querySelectorAll('a[data-copy]').forEach(function(a){a.addEventListener('click',function(e){if(!navigator.clipboard)return;e.preventDefault();var t=a.textContent;navigator.clipboard.writeText(a.dataset.copy).then(function(){a.textContent='Copied';a.classList.add('ok');document.querySelector('.sr').textContent='Email address copied';setTimeout(function(){a.textContent=t;a.classList.remove('ok')},1600)},function(){location.href=a.href})})})</script>"""

ANALYTICS = """<script>window.goatcounter={no_onload:false,allow_local:false,path:function(p){var r=goatcounter.get_query('r');return location.pathname+(r?'?r='+encodeURIComponent(r):'')}}</script>
<script data-goatcounter="https://{code}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>"""


def page(site, title, desc, url, image, body, feed=True):
    analytics = ANALYTICS.replace("{code}", site["goatcounter"]) if site.get("goatcounter") else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#f7f5f0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#151412" media="(prefers-color-scheme: dark)">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(desc, quote=True)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:site_name" content="{html.escape(site['name'], quote=True)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title, quote=True)}">
<meta name="twitter:description" content="{html.escape(desc, quote=True)}">
<meta name="twitter:image" content="{image}">
<link rel="alternate" type="application/rss+xml" title="{html.escape(site['name'], quote=True)}" href="/feed.xml">
<link rel="preload" href="/fonts/a.woff2" as="font" type="font/woff2" crossorigin>
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon-32.png" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>{CSS}</style>
</head>
<body>
{body}
{analytics}
</body>
</html>
"""


def render_post(site, post, newer, older):
    url = f"{site['domain']}/{post['slug']}/"
    parts = []
    if post["picture"]:
        parts.append(f'<img class="pic" src="/{post["slug"]}/picture.jpg" alt="{html.escape(post["alt"], quote=True)}" width="1200" height="900">')
    parts.append(f'<p class="t">{html.escape(post["title"])} · <time datetime="{post["date"]:%Y-%m-%d}">{post["date"]:%-d %b %Y}</time></p>')
    parts.append('<div class="body">' + "".join(f"<p>{p}</p>" for p in post["paras_html"]) + "</div>")
    share = "https://x.com/intent/post?text=" + quote(post["title"]) + "&url=" + quote(url, safe="") + "&via=sidvent"
    parts.append(f'<p class="share"><a href="{share}" target="_blank" rel="noopener">Share on X</a></p>')
    parts.append(f'<p class="id"><a href="/">{html.escape(site["name"])}</a></p>')
    nav = []
    if older:
        nav.append(f'<a href="/{older["slug"]}/">Previous</a>')
    if newer:
        nav.append(f'<a href="/{newer["slug"]}/">Next</a>')
    if nav:
        parts.append('<p class="nav">' + "".join(nav) + "</p>")
    desc = post["first"] or post["title"]
    return page(site, post["title"], desc, url, f"{site['domain']}/og/{post['slug']}.png", "\n".join(parts))


def render_home(site, posts):
    blink = ' class="blink"' if site.get("dot_blink", "").lower() in ("yes", "true", "on") else ""
    parts = [f'<h1{blink}>{html.escape(site["name"])}<span class="dot">.</span></h1>', site["intro_html"]]
    if blink:
        parts.append("<script>(function(){var h=document.querySelector('h1.blink');function s(){h.classList.add('still')}addEventListener('scroll',s,{once:true,passive:true})})()</script>")
    if site["socials"]:
        links = []
        for n, u in site["socials"].items():
            if u.startswith("mailto:"):
                links.append(f'<a href="{html.escape(u, quote=True)}" data-copy="{html.escape(u[7:], quote=True)}">{html.escape(n)}</a>')
            else:
                links.append(f'<a href="{html.escape(u, quote=True)}">{html.escape(n)}</a>')
        parts.append('<p class="soc">' + "".join(links) + "</p>")
        parts.append(COPY_JS)
    rows = "".join(
        f'<a href="/{p["slug"]}/"><time datetime="{p["date"]:%Y-%m-%d}">{p["date"]:%-d %b %Y}</time><span>{html.escape(p["title"])}</span></a>'
        for p in posts
    )
    parts.append(f'<div class="list">{rows}</div>')
    desc = first_sentence(re.sub(r"<[^>]+>", "", site["intro_html"]))
    return page(site, site["name"], desc, site["domain"] + "/", f"{site['domain']}/og/home.png", "\n".join(parts))


def render_404(site):
    body = f'<p class="t">Not found</p><div class="body"><p>Nothing here. Even robots take a wrong turn sometimes.</p></div><p class="id"><a href="/">{html.escape(site["name"])}</a></p>'
    return page(site, "Not found", "Not found", site["domain"] + "/404", f"{site['domain']}/og/home.png", body)


def render_feed(site, posts):
    items = []
    for p in posts:
        link = f"{site['domain']}/{p['slug']}/"
        content = "".join(f"<p>{x}</p>" for x in p["paras_html"])
        items.append(
            f"<item><title>{html.escape(p['title'])}</title><link>{link}</link><guid>{link}</guid>"
            f"<pubDate>{format_datetime(p['date'])}</pubDate><description>{html.escape(content)}</description></item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>{html.escape(site['name'])}</title><link>{site['domain']}/</link>"
        f"<description>{html.escape(site.get('tagline') or site['name'])}</description>{''.join(items)}</channel></rss>"
    )


# ---------------------------------------------------------------- images

def _card_font():
    """Variable TTF for Pillow, converted once from the site's woff2."""
    global _CARD_TTF
    try:
        return _CARD_TTF
    except NameError:
        pass
    from fontTools.ttLib import TTFont
    import tempfile
    f = TTFont(FONTS / "whysid-sans.woff2")
    f.flavor = None
    path = Path(tempfile.gettempdir()) / "whysid-sans.ttf"
    f.save(path)
    _CARD_TTF = str(path)
    return _CARD_TTF


def card(site, post, out_path):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1200, 630
    bg, fg, mute, accent = "#f7f5f0", "#1c1b19", "#6b6761", "#b8401f"
    ttf = _card_font()

    def font(size, weight):
        f = ImageFont.truetype(ttf, size)
        f.set_variation_by_axes([weight])
        return f

    def greedy(d, words, f, width):
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if cur and d.textlength(t, font=f) > width:
                lines.append(cur)
                cur = w
            else:
                cur = t
        if cur:
            lines.append(cur)
        return lines

    def wrap(d, text, f, width, max_lines):
        """Balanced wrap: same line count as greedy, but even line lengths."""
        words = text.split()
        n = len(greedy(d, words, f, width))
        lo, hi = 50, width
        while lo < hi:
            mid = (lo + hi) // 2
            if len(greedy(d, words, f, mid)) <= n:
                hi = mid
            else:
                lo = mid + 1
        lines = greedy(d, words, f, lo)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(".,;:") + "\u2026"
        return lines

    def name_with_dot(d, x, y, size):
        f = font(size, 600)
        d.text((x, y), site["name"], font=f, fill=fg)
        d.text((x + d.textlength(site["name"], font=f), y), ".", font=f, fill=accent)

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    if post is None:  # home card
        name_with_dot(d, 96, 112, 72)
        lines = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<p>(.*?)</p>", site["intro_html"])]
        lines = [html.unescape(l) for l in lines]
        y = 112 + 72 * 1.2 + 28
        if lines:
            d.text((96, y), lines[0], font=font(34, 380), fill=fg)
            y += 34 * 1.5 + 22
        for l in lines[1:3]:
            d.text((96, y), l, font=font(26, 380), fill=mute)
            y += 26 * 1.5
        d.text((96, H - 96 - 22), "whysid.com", font=font(22, 380), fill=mute)
    elif post["picture"]:
        pic = Image.open(post["picture"]).convert("RGB")
        pw, ph = 760, 630
        scale = max(pw / pic.width, ph / pic.height)
        pic = pic.resize((round(pic.width * scale), round(pic.height * scale)), Image.LANCZOS)
        left, top = (pic.width - pw) // 2, (pic.height - ph) // 2
        img.paste(pic.crop((left, top, left + pw, top + ph)), (0, 0))
        x, width = 816, 336
        ft, fb = font(40, 600), font(22, 380)
        y = 64
        for line in wrap(d, post["title"], ft, width, 4):
            d.text((x, y), line, font=ft, fill=fg)
            y += 40 * 1.2
        y += 20
        for line in wrap(d, post["first"], fb, width, 5):
            d.text((x, y), line, font=fb, fill=mute)
            y += 22 * 1.5
        name_with_dot(d, x, H - 64 - 22, 22)
    else:
        ft, fb = font(64, 600), font(30, 380)
        y = 104
        for line in wrap(d, post["title"], ft, 1000, 3):
            d.text((96, y), line, font=ft, fill=fg)
            y += 64 * 1.15
        y += 28
        for line in wrap(d, post["first"], fb, 960, 3):
            d.text((96, y), line, font=fb, fill=mute)
            y += 30 * 1.45
        name_with_dot(d, 96, H - 96 - 26, 26)
        date = f"{post['date']:%-d %b %Y}"
        fd = font(22, 380)
        d.text((W - 96 - d.textlength(date, font=fd), H - 96 - 22), date, font=fd, fill=mute)

    img.save(out_path, "PNG", optimize=True)


def picture(post, out_path):
    from PIL import Image

    pic = Image.open(post["picture"]).convert("RGB")
    W, H = 1200, 900
    scale = max(W / pic.width, H / pic.height)
    pic = pic.resize((round(pic.width * scale), round(pic.height * scale)), Image.LANCZOS)
    left, top = (pic.width - W) // 2, (pic.height - H) // 2
    pic.crop((left, top, left + W, top + H)).save(out_path, "JPEG", quality=80, optimize=True, progressive=True)


# ---------------------------------------------------------------- main

def main():
    site = load_site()
    posts = load_posts()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "fonts").mkdir(parents=True)
    (OUT / "og").mkdir()
    shutil.copy(FONTS / "whysid-sans.woff2", OUT / "fonts" / "a.woff2")
    for f in (ROOT / "static").iterdir():
        shutil.copy(f, OUT / f.name)

    (OUT / "index.html").write_text(render_home(site, posts), encoding="utf-8")
    (OUT / "404.html").write_text(render_404(site), encoding="utf-8")
    (OUT / "feed.xml").write_text(render_feed(site, posts), encoding="utf-8")
    (OUT / "_headers").write_text("/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n/og/*\n  Cache-Control: public, max-age=86400\n", encoding="utf-8")
    card(site, None, OUT / "og" / "home.png")

    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        d = OUT / p["slug"]
        d.mkdir()
        (d / "index.html").write_text(render_post(site, p, newer, older), encoding="utf-8")
        if p["picture"]:
            picture(p, d / "picture.jpg")
        card(site, p, OUT / "og" / f"{p['slug']}.png")
        size = sum(f.stat().st_size for f in d.iterdir()) + (OUT / "fonts" / "a.woff2").stat().st_size
        flag = "  (over 300 KB)" if size > 300_000 else ""
        print(f"/{p['slug']}/  {p['words']} words  {size // 1024} KB{flag}")
    print(f"home + {len(posts)} posts built into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
