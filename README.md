# whysid.com

A static site. Each post is one text file. Nothing here needs touching except the two things below.

## Add a post

Create a file in `posts/`, named `YYYY-MM-DD-a-few-words.md`:

```
---
title: The robot should look unsure
date: 2026-10-24
---
The paragraph. 40 to 180 words. A [link](https://example.com) is written like this.

? The question that ends the post.
```

For a post with a picture, put the image file in `posts/` too and add two lines:

```
---
title: Side by side
date: 2026-10-10
picture: side-by-side.jpg
alt: A pencil sketch of a robot arm next to a person's hands, doing the same task
---
```

Pictures are cropped to 4:3 and resized at build time, so any size works. The `alt` line is what a screen reader says and what shows if the picture fails to load.

Commit the file. The site rebuilds and is live in about a minute. The post's address is its title in lower case with hyphens (`/the-robot-should-look-unsure/`); add a `slug: short-name` line to choose a different one.

## Change the intro or socials

Edit `site.md`. The text under the front matter is the intro. Socials are `Name: URL` lines; add or remove as you like.

## Build locally (optional)

```
pip install -r requirements.txt
python3 build.py
```

Output goes to `site/`.

## Hosting

Cloudflare Pages, connected to this repository.
Build command: `pip install -r requirements.txt && python3 build.py`
Output directory: `site`

Analytics: GoatCounter, cookie-free. Set `goatcounter:` in `site.md` to the site code and the page view, with any `?r=` code from the link, is recorded.

Fonts: Atkinson Hyperlegible, SIL Open Font License, see `fonts/OFL.txt`.
