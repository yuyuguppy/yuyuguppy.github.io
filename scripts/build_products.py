#!/usr/bin/env python3
"""Generate crawlable product HTML for 宇魚水族 from the inventory CSV.

The script keeps fish.html's interactive Google Sheet shop, but adds a static
HTML product list for crawlers and creates one canonical page per main product.
It also refreshes sitemap.xml.  It uses only Python's standard library so it can
run inside GitHub Actions without installing dependencies.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse


SITE = "https://yuyuguppy.github.io"
STORE_NAME = "宇魚水族"
STORE_ID = f"{SITE}/#petstore"

CATEGORIES = {
    "guppy": ("孔雀魚", "宇魚水族精選孔雀魚，提供新竹新埔門市挑選、飼養諮詢與專業活體配送。"),
    "molly": ("茉莉魚", "宇魚水族精選茉莉魚，提供新竹新埔門市挑選、飼養諮詢與專業活體配送。"),
    "shrimp": ("蝦子、螺類與底棲生物", "宇魚水族精選米蝦、觀賞螺與底棲生物，適合豐富小型水族箱生態。"),
    "addon": ("水族用品", "宇魚水族實際使用與精選的水族用品，可搭配活體或至門市選購。"),
    "tank": ("魚缸", "宇魚水族精選魚缸與相關設備，並提供魚缸規劃、客製及到府安裝諮詢。"),
}

STATIC_START = "<!-- STATIC_PRODUCTS_START: 由 scripts/build_products.py 自動產生，請勿手動修改 -->"
STATIC_END = "<!-- STATIC_PRODUCTS_END -->"
SCHEMA_START = "<!-- STATIC_PRODUCT_SCHEMA_START -->"
SCHEMA_END = "<!-- STATIC_PRODUCT_SCHEMA_END -->"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def text_only(value: object) -> str:
    value = re.sub(r"<[^>]*>", " ", str(value or ""))
    return clean(html.unescape(value))


def money(value: object) -> int:
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    return int(digits or 0)


def stock(value: object) -> int:
    try:
        return int(float(clean(value) or 0))
    except ValueError:
        return 0


def h(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def absolute_asset(path: str) -> str:
    path = clean(path)
    if not path:
        return f"{SITE}/logo.jpg"
    if urlparse(path).scheme in {"http", "https"}:
        return path
    return f"{SITE}/{path.lstrip('/')}"


def product_page_asset(path: str) -> str:
    path = clean(path)
    if not path:
        return "../logo.jpg"
    if urlparse(path).scheme in {"http", "https", "data"}:
        return path
    return "../" + path.lstrip("/")


def product_name(row: dict[str, str]) -> str:
    base = base_name(row)
    variant = clean(row.get("variant_name"))
    if variant == "無規格":
        variant = ""
    return clean(f"{base} {variant}")


def base_name(row: dict[str, str]) -> str:
    return clean(row.get("display_name")) or clean(row.get("name"))


def main_id(product_id: str) -> str:
    return re.sub(r"-\d+$", "", product_id)


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    rows = [row for row in rows if clean(row.get("id")) and clean(row.get("name"))]
    for row in rows:
        for key, value in list(row.items()):
            row[key] = clean(value)
    return rows


def validate(rows: list[dict[str, str]]) -> None:
    required = {"id", "name", "price", "category", "stock", "img", "slug"}
    if not rows:
        raise ValueError("CSV 沒有可用商品")
    missing = required - rows[0].keys()
    if missing:
        raise ValueError("CSV 缺少欄位：" + ", ".join(sorted(missing)))
    ids = [row["id"] for row in rows]
    slugs = [row["slug"] for row in rows]
    dup_ids = sorted({x for x in ids if ids.count(x) > 1})
    dup_slugs = sorted({x for x in slugs if slugs.count(x) > 1})
    if dup_ids or dup_slugs:
        raise ValueError(f"重複 id={dup_ids}；重複 slug={dup_slugs}")
    bad_slugs = [s for s in slugs if not re.fullmatch(r"[a-z0-9-]+", s)]
    if bad_slugs:
        raise ValueError("slug 只能使用小寫英數與連字號：" + ", ".join(bad_slugs[:5]))


def group_products(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
    mains = [row for row in rows if row["category"].lower() != "sub"]
    main_ids = {row["id"] for row in mains}
    variants: dict[str, list[dict[str, str]]] = {row["id"]: [] for row in mains}
    for row in rows:
        if row["category"].lower() == "sub":
            parent = main_id(row["id"])
            if parent in main_ids:
                variants[parent].append(row)
            else:
                print(f"警告：找不到規格 {row['id']} 的主要商品 {parent}", file=sys.stderr)
    return mains, variants


def description(row: dict[str, str]) -> str:
    intro = text_only(row.get("intro"))
    if intro:
        return intro
    category = row.get("category", "").lower()
    category_label, fallback = CATEGORIES.get(category, ("水族商品", "查看宇魚水族商品價格、庫存與購買資訊。"))
    return f"{product_name(row)}是宇魚水族提供的{category_label}。{fallback}"


def image_list(row: dict[str, str]) -> list[str]:
    paths = [row.get("img", "")]
    paths.extend(p.strip() for p in row.get("more_images", "").split(",") if p.strip())
    result: list[str] = []
    for path in paths:
        url = absolute_asset(path)
        if url not in result:
            result.append(url)
    return result or [f"{SITE}/logo.jpg"]


def offer(row: dict[str, str], buy_url: str) -> dict[str, object]:
    return {
        "@type": "Offer",
        "url": buy_url,
        "priceCurrency": "TWD",
        "price": str(money(row.get("price"))),
        "availability": "https://schema.org/InStock" if stock(row.get("stock")) > 0 else "https://schema.org/OutOfStock",
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {"@type": "PetStore", "@id": STORE_ID, "name": STORE_NAME},
    }


def static_card(row: dict[str, str]) -> str:
    name = product_name(row)
    slug = row["slug"]
    sold_out = stock(row.get("stock")) <= 0
    tag = row.get("tag", "").upper()
    tag_html = ""
    if tag == "HOT":
        tag_html = '<div class="p-tag tag-hot">熱銷 🔥</div>'
    elif tag == "NEW":
        tag_html = '<div class="p-tag tag-new">新品 ✨</div>'
    elif tag == "SALE":
        tag_html = '<div class="p-tag tag-sale">特價 💰</div>'
    price = money(row.get("price"))
    original = money(row.get("origin_price"))
    if tag == "SALE" and original > price:
        price_html = f'<span class="p-price-current"><span class="price-origin">NT$ {original:,}</span><span class="price-sale">NT$ {price:,}</span></span>'
    else:
        price_html = f'<span class="p-price-current">NT$ {price:,}</span>'
    sold_mask = '<div class="sold-out-mask">SOLD OUT</div>' if sold_out else ""
    status = "目前售完・查看商品" if sold_out else "查看商品與規格"
    return f'''<article class="product-card static-product-card" data-product-id="{h(row['id'])}">
  {tag_html}
  <a href="products/{h(slug)}.html" class="static-product-link" aria-label="查看{h(name)}商品介紹">
    <div class="p-img-box">
      <img src="{h(row.get('img') or 'logo.jpg')}" alt="{h(name)}｜宇魚水族" class="p-img" loading="lazy" decoding="async" onerror="this.src='logo.jpg'">
      {sold_mask}
    </div>
    <div class="p-info">
      <h2 class="p-name" style="margin:0">{h(name)}</h2>
      {price_html}
      <span class="add-btn{' disabled' if sold_out else ''}" style="display:block;text-align:center">{status}</span>
    </div>
  </a>
</article>'''


def item_list_schema(mains: list[dict[str, str]]) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "宇魚水族商品列表",
        "numberOfItems": len(mains),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "url": f"{SITE}/products/{row['slug']}.html",
                "name": product_name(row),
            }
            for index, row in enumerate(mains, 1)
        ],
    }
    return '<script type="application/ld+json" id="staticProductListSchema">\n' + json.dumps(data, ensure_ascii=False, indent=2) + "\n</script>"


def replace_between(source: str, start: str, end: str, content: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    replacement = start + "\n" + content + "\n" + end
    if pattern.search(source):
        return pattern.sub(lambda _: replacement, source, count=1)
    raise ValueError(f"找不到更新標記：{start}")


def update_fish_html(fish_path: Path, mains: list[dict[str, str]]) -> None:
    source = fish_path.read_text(encoding="utf-8")
    cards = "\n".join(static_card(row) for row in mains)
    static_block = f"{STATIC_START}\n{cards}\n{STATIC_END}"

    if STATIC_START in source:
        source = replace_between(source, STATIC_START, STATIC_END, cards)
    else:
        empty_container = re.compile(r'(<div\s+class="products-grid"\s+id="productContainer"\s*>).*?(</div>)', re.S)
        if not empty_container.search(source):
            raise ValueError("fish.html 找不到 productContainer")
        source = empty_container.sub(lambda m: m.group(1) + "\n" + static_block + "\n" + m.group(2), source, count=1)

    schema = item_list_schema(mains)
    if SCHEMA_START in source:
        source = replace_between(source, SCHEMA_START, SCHEMA_END, schema)
    else:
        source = source.replace("</head>", f"    {SCHEMA_START}\n    {schema}\n    {SCHEMA_END}\n</head>", 1)

    css = '''
    /* 靜態 SEO 商品卡：載入試算表後會由原本購物介面接手 */
    .static-product-link { color: inherit; text-decoration: none; display: block; height: 100%; }
    .static-product-card h2 { font-size: inherit; font-weight: inherit; }
    '''
    marker = "/* STATIC_PRODUCT_CSS */"
    if marker not in source:
        source = source.replace("</style>", f"\n    {marker}\n{css}</style>", 1)

    fish_path.write_text(source, encoding="utf-8", newline="\n")


def schema_for_product(row: dict[str, str], variant_rows: list[dict[str, str]]) -> dict[str, object]:
    canonical = f"{SITE}/products/{row['slug']}.html"
    all_rows = [row, *variant_rows]
    page_name = base_name(row) if variant_rows else product_name(row)
    category_label = CATEGORIES.get(row.get("category", "").lower(), ("水族商品", ""))[0]

    breadcrumb = {
        "@type": "BreadcrumbList",
        "@id": f"{canonical}#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "宇魚水族", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "活體與商品專區", "item": f"{SITE}/fish.html"},
            {"@type": "ListItem", "position": 3, "name": page_name, "item": canonical},
        ],
    }

    if variant_rows:
        group_name = base_name(row)
        product = {
            "@type": "ProductGroup",
            "@id": f"{canonical}#product",
            "productGroupID": row["id"],
            "name": group_name,
            "description": description(row),
            "url": canonical,
            "image": image_list(row),
            "brand": {"@type": "Brand", "name": STORE_NAME},
            "category": category_label,
            "hasVariant": [],
        }
        for item in all_rows:
            buy_url = f"{SITE}/fish.html?product={quote(item['slug'])}"
            product["hasVariant"].append({
                "@type": "Product",
                "sku": item["id"],
                "name": product_name(item),
                "description": description(item) if item.get("intro") else description(row),
                "image": image_list(item),
                "url": buy_url,
                "size": clean(item.get("variant_name")) or "主要規格",
                "offers": offer(item, buy_url),
            })
    else:
        buy_url = f"{SITE}/fish.html?product={quote(row['slug'])}"
        product = {
            "@type": "Product",
            "@id": f"{canonical}#product",
            "sku": row["id"],
            "name": product_name(row),
            "description": description(row),
            "url": canonical,
            "image": image_list(row),
            "brand": {"@type": "Brand", "name": STORE_NAME},
            "category": category_label,
            "offers": offer(row, buy_url),
        }
    return {"@context": "https://schema.org", "@graph": [breadcrumb, product]}


def product_page(row: dict[str, str], variant_rows: list[dict[str, str]], related: list[dict[str, str]]) -> str:
    name = base_name(row) if variant_rows else product_name(row)
    desc = description(row)
    short_desc = desc[:155]
    canonical = f"{SITE}/products/{row['slug']}.html"
    category_label = CATEGORIES.get(row.get("category", "").lower(), ("水族商品", ""))[0]
    all_rows = [row, *variant_rows]
    any_in_stock = any(stock(item.get("stock")) > 0 for item in all_rows)
    status_text = "現貨供應中" if any_in_stock else "目前售完，可私訊詢問下一批"
    status_class = "in-stock" if any_in_stock else "out-stock"
    images = [row.get("img", "")]
    images.extend(x.strip() for x in row.get("more_images", "").split(",") if x.strip())
    images = [x for i, x in enumerate(images) if x and x not in images[:i]] or ["logo.jpg"]
    gallery = "".join(
        f'<img src="{h(product_page_asset(path))}" alt="{h(name)}商品照片{index}" loading="lazy" decoding="async" onerror="this.src=\'../logo.jpg\'">'
        for index, path in enumerate(images, 1)
    )
    intro_html = "".join(f"<p>{h(paragraph)}</p>" for paragraph in re.split(r"\n+", str(row.get("intro") or "")) if clean(paragraph))
    if not intro_html:
        intro_html = f"<p>{h(desc)}</p>"

    variant_lines = []
    for item in all_rows:
        item_name = product_name(item)
        item_stock = stock(item.get("stock"))
        item_status = "有現貨" if item_stock > 0 else "暫時售完"
        item_status_class = "in-stock" if item_stock > 0 else "out-stock"
        buy_url = f"../fish.html?product={quote(item['slug'])}"
        variant_lines.append(f'''<tr>
  <th scope="row">{h(clean(item.get('variant_name')) or item_name)}</th>
  <td>NT$ {money(item.get('price')):,}</td>
  <td><span class="status {item_status_class}">{item_status}</span></td>
  <td><a class="small-button" href="{h(buy_url)}">前往選購</a></td>
</tr>''')
    related_html = "".join(
        f'<a class="related-card" href="{h(other["slug"])}.html"><img src="{h(product_page_asset(other.get("img") or "logo.jpg"))}" alt="{h(product_name(other))}" loading="lazy"><span>{h(product_name(other))}</span></a>'
        for other in related
    )
    notice = text_only(row.get("notice"))
    notice_html = f'<section class="notice"><h2>購買注意事項</h2><p>{h(notice)}</p></section>' if notice else ""
    schema = json.dumps(schema_for_product(row, variant_rows), ensure_ascii=False, indent=2)
    buy_url = f"../fish.html?product={quote(row['slug'])}"
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{h(name)}｜價格、庫存與購買｜宇魚水族</title>
  <meta name="description" content="{h(short_desc)}">
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
  <link rel="canonical" href="{h(canonical)}">
  <meta property="og:locale" content="zh_TW">
  <meta property="og:type" content="product">
  <meta property="og:site_name" content="宇魚水族">
  <meta property="og:title" content="{h(name)}｜宇魚水族">
  <meta property="og:description" content="{h(short_desc)}">
  <meta property="og:url" content="{h(canonical)}">
  <meta property="og:image" content="{h(absolute_asset(row.get('img') or 'logo.jpg'))}">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">{schema}</script>
  <style>
    :root {{ color-scheme: dark; --aqua:#64ffda; --yellow:#ffe100; --panel:#0d253f; --muted:#bcccdc; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(circle at 50% 5%,#1a3c5e 0%,#03101f 72%); color:#f0f4f8; font-family:"Microsoft JhengHei",sans-serif; line-height:1.75; }}
    a {{ color:var(--aqua); }}
    .wrap {{ width:min(1080px,calc(100% - 32px)); margin:auto; padding:24px 0 60px; }}
    .top {{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:20px; }}
    .brand {{ display:flex; align-items:center; gap:10px; color:var(--aqua); text-decoration:none; font-size:20px; font-weight:700; }}
    .brand img {{ width:44px; height:44px; object-fit:cover; border-radius:50%; }}
    .back {{ text-decoration:none; border:1px solid var(--aqua); border-radius:999px; padding:7px 14px; }}
    .breadcrumb {{ color:var(--muted); font-size:14px; margin:10px 0 22px; }}
    .breadcrumb a {{ color:var(--muted); }}
    .hero {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(300px,0.9fr); gap:30px; align-items:start; }}
    .gallery {{ display:grid; grid-template-columns:repeat(2,1fr); gap:10px; }}
    .gallery img {{ width:100%; aspect-ratio:1/1; object-fit:cover; border-radius:16px; background:#071827; border:1px solid rgba(100,255,218,.25); }}
    .gallery img:first-child:last-child {{ grid-column:1/-1; }}
    .panel,.section {{ background:rgba(13,37,63,.94); border:1px solid rgba(100,255,218,.25); border-radius:18px; padding:24px; box-shadow:0 12px 30px rgba(0,0,0,.25); }}
    .eyebrow {{ color:var(--yellow); font-weight:700; }}
    h1 {{ margin:6px 0 8px; font-size:clamp(28px,5vw,42px); line-height:1.25; }}
    h2 {{ color:var(--aqua); line-height:1.35; margin-top:0; }}
    .price {{ color:var(--yellow); font-weight:800; font-size:28px; margin:10px 0; }}
    .status {{ display:inline-block; padding:3px 10px; border-radius:999px; font-weight:700; font-size:14px; }}
    .in-stock {{ color:#8effcb; background:rgba(0,170,110,.2); }}
    .out-stock {{ color:#ffb1b1; background:rgba(255,70,70,.16); }}
    .button,.small-button {{ display:inline-block; text-decoration:none; background:var(--aqua); color:#03101f; border-radius:999px; font-weight:800; }}
    .button {{ padding:12px 22px; margin-top:14px; }}
    .small-button {{ padding:5px 11px; white-space:nowrap; }}
    .section {{ margin-top:24px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ padding:12px 8px; border-bottom:1px solid rgba(255,255,255,.1); text-align:left; }}
    .facts {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px 22px; padding:0; list-style:none; }}
    .facts strong {{ color:var(--aqua); display:block; }}
    .notice {{ border-left:4px solid var(--yellow); background:rgba(255,225,0,.08); padding:18px 20px; margin-top:24px; border-radius:8px; }}
    .notice h2 {{ color:var(--yellow); font-size:20px; }}
    .related {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
    .related-card {{ color:#fff; text-decoration:none; background:#071827; border-radius:12px; overflow:hidden; border:1px solid rgba(255,255,255,.1); }}
    .related-card img {{ width:100%; aspect-ratio:1/1; object-fit:cover; display:block; }}
    .related-card span {{ display:block; padding:10px; }}
    footer {{ color:var(--muted); text-align:center; margin-top:38px; font-size:14px; }}
    @media(max-width:760px) {{ .hero {{ grid-template-columns:1fr; }} .related {{ grid-template-columns:repeat(2,1fr); }} .facts {{ grid-template-columns:1fr; }} .variant-table {{ overflow-x:auto; }} table {{ min-width:560px; }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <header class="top">
      <a class="brand" href="../index.html"><img src="../logo.jpg" alt="宇魚水族標誌">宇魚水族</a>
      <a class="back" href="../fish.html">回活體與商品專區</a>
    </header>
    <nav class="breadcrumb" aria-label="麵包屑"><a href="../index.html">首頁</a> › <a href="../fish.html">活體與商品專區</a> › {h(name)}</nav>
    <div class="hero">
      <div class="gallery">{gallery}</div>
      <section class="panel">
        <div class="eyebrow">{h(category_label)}｜新竹新埔宇魚水族</div>
        <h1>{h(name)}</h1>
        <span class="status {status_class}">{h(status_text)}</span>
        <div class="price">NT$ {money(row.get('price')):,} 起</div>
        <div>{intro_html}</div>
        <a class="button" href="{h(buy_url)}">查看即時庫存並選購</a>
      </section>
    </div>
    <section class="section">
      <h2>價格、規格與庫存</h2>
      <div class="variant-table"><table><thead><tr><th>規格</th><th>價格</th><th>狀態</th><th>選購</th></tr></thead><tbody>{''.join(variant_lines)}</tbody></table></div>
    </section>
    <section class="section">
      <h2>商品與購買資訊</h2>
      <ul class="facts">
        <li><strong>商品編號</strong>{h(row['id'])}</li>
        <li><strong>商品分類</strong>{h(category_label)}</li>
        <li><strong>門市位置</strong>新竹縣新埔鎮義民路二段630巷9號</li>
        <li><strong>購買方式</strong>門市挑選／網站下單；活體提供專業包裝配送</li>
      </ul>
    </section>
    {notice_html}
    <section class="section"><h2>同類商品推薦</h2><div class="related">{related_html}</div></section>
    <footer>宇魚水族｜把養魚變簡單・找回單純的快樂</footer>
  </main>
</body>
</html>
'''


def write_product_pages(root: Path, mains: list[dict[str, str]], variants: dict[str, list[dict[str, str]]]) -> None:
    products_dir = root / "products"
    if products_dir.exists():
        shutil.rmtree(products_dir)
    products_dir.mkdir(parents=True)
    by_category: dict[str, list[dict[str, str]]] = {}
    for row in mains:
        by_category.setdefault(row.get("category", ""), []).append(row)
    for row in mains:
        related = [x for x in by_category.get(row.get("category", ""), []) if x["id"] != row["id"]][:6]
        output = products_dir / f"{row['slug']}.html"
        output.write_text(product_page(row, variants.get(row["id"], []), related), encoding="utf-8", newline="\n")


def write_sitemap(root: Path, mains: list[dict[str, str]]) -> None:
    today = date.today().isoformat()
    fixed = [
        (f"{SITE}/", "weekly", "1.0"),
        (f"{SITE}/fish.html", "daily", "0.9"),
        (f"{SITE}/about.html", "monthly", "0.7"),
        (f"{SITE}/portfolio.html", "monthly", "0.8"),
    ]
    urls = []
    for url, freq, priority in fixed:
        urls.append(f"  <url><loc>{h(url)}</loc><lastmod>{today}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>")
    for row in mains:
        url = f"{SITE}/products/{row['slug']}.html"
        urls.append(f"  <url><loc>{h(url)}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    (root / "sitemap.xml").write_text(xml, encoding="utf-8", newline="\n")


def obtain_csv(args: argparse.Namespace) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if args.csv_url:
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "inventory.csv"
        request = urllib.request.Request(args.csv_url, headers={"User-Agent": "Mozilla/5.0 YuyuProductBuilder/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            path.write_bytes(response.read())
        return path, temporary
    if not args.csv:
        raise ValueError("請提供 --csv 或 --csv-url")
    return Path(args.csv), None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="本機 CSV 路徑")
    parser.add_argument("--csv-url", help="已發布的 Google Sheet CSV 網址")
    parser.add_argument("--fish", default="fish.html", help="fish.html 路徑")
    parser.add_argument("--site-root", default=".", help="網站根目錄")
    args = parser.parse_args()
    csv_path, temporary = obtain_csv(args)
    try:
        rows = read_rows(csv_path)
        validate(rows)
        mains, variants = group_products(rows)
        root = Path(args.site_root)
        update_fish_html(Path(args.fish), mains)
        write_product_pages(root, mains, variants)
        write_sitemap(root, mains)
        print(f"完成：{len(mains)} 個主要商品頁、{sum(len(v) for v in variants.values())} 個規格、fish.html 靜態清單與 sitemap.xml")
    finally:
        if temporary:
            temporary.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
