/* 宇魚共用選單 v1 — 僅更新導覽，不修改商品、購物車或訂單流程。 */
(function () {
  'use strict';
  const script = document.currentScript;
  const base = new URL('.', script ? script.src : location.href);
  const url = path => new URL(path, base).href;
  function init() {
    if (document.getElementById('yuyu-menu-style')) return;
    const page = location.pathname.split('/').pop() || 'index.html';
    const warm = page === 'betta.html';
    const font = document.createElement('link');
    font.rel = 'stylesheet';
    font.href = 'https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@700&display=swap';
    document.head.appendChild(font);
    const style = document.createElement('style');
    style.id = 'yuyu-menu-style';
    style.textContent = `
      html{scroll-padding-top:calc(var(--yuyu-ann-height,0px) + 70px)}
      body.yuyu-menu-ready{padding-top:calc(var(--yuyu-ann-height,0px) + 56px)!important}
      .yuyu-menu-header,#mySidenav.yuyu-menu-drawer{--menu-bg:#03101f;--menu-ink:#f0f4f8;--menu-accent:#64ffda;--menu-line:#334e68}
      .yuyu-menu-header.yuyu-warm,#mySidenav.yuyu-warm{--menu-bg:#fff6e9;--menu-ink:#503d30;--menu-accent:#885327;--menu-line:#dbc3a8}
      .yuyu-menu-header{position:fixed;top:var(--yuyu-ann-height,0px);left:0;width:100%;height:56px;box-sizing:border-box;z-index:11000;display:flex;align-items:center;justify-content:space-between;padding:0 14px;background:var(--menu-bg);color:var(--menu-ink);border-bottom:1px solid var(--menu-line);box-shadow:0 3px 12px #0002}
      .yuyu-menu-header .hamburger-btn{display:flex;flex-direction:column;justify-content:center;align-items:center;gap:5px;width:44px;height:44px;padding:8px;border:0;background:transparent;cursor:pointer;position:relative;z-index:2}
      .yuyu-menu-header .bar{display:block;width:25px;height:3px;border-radius:3px;background:var(--menu-accent)}
      .yuyu-menu-header .yuyu-brand{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font:700 20px/1.4 'Zen Maru Gothic','Microsoft JhengHei',sans-serif;color:var(--menu-accent);text-decoration:none;white-space:nowrap}
      .yuyu-menu-header .yuyu-mark{display:block;width:38px;height:38px;object-fit:contain}
      .yuyu-menu-header .mobile-cart-btn{position:relative;display:block;min-width:44px;min-height:44px;margin:0;padding:8px;border:0;background:transparent;color:var(--menu-accent);font-size:22px;cursor:pointer}
      #mySidenav.yuyu-menu-drawer{position:fixed;inset:0 auto 0 0;z-index:13000;width:min(320px,90vw);height:100vh;height:100dvh;box-sizing:border-box;padding:62px 12px 24px;overflow:auto;overscroll-behavior:contain;background:var(--menu-bg);color:var(--menu-ink);border:0;border-right:1px solid var(--menu-line);transform:translateX(-101%);visibility:hidden;transition:transform .22s ease,visibility .22s;box-shadow:8px 0 30px #0003}
      #mySidenav.yuyu-menu-drawer.yuyu-open{transform:translateX(0);visibility:visible}
      #mySidenav.yuyu-menu-drawer nav{display:block;margin:0;padding:0}
      #mySidenav.yuyu-menu-drawer a,#mySidenav.yuyu-menu-drawer button{box-sizing:border-box;display:block;width:100%;margin:0;padding:12px 14px;min-height:46px;border:0;border-radius:9px;background:transparent;color:var(--menu-ink);font:700 18px/1.6 'Zen Maru Gothic','Microsoft JhengHei',sans-serif;letter-spacing:.03em;text-align:left;text-decoration:none;white-space:normal;cursor:pointer}
      #mySidenav.yuyu-menu-drawer a:hover,#mySidenav.yuyu-menu-drawer button:hover,#mySidenav.yuyu-menu-drawer a[aria-current=page]{background:color-mix(in srgb,var(--menu-accent) 14%,transparent);color:var(--menu-accent)}
      #mySidenav.yuyu-menu-drawer a[aria-current=page]{box-shadow:inset 3px 0 var(--menu-accent)}
      #mySidenav.yuyu-menu-drawer .closebtn{position:absolute;top:9px;right:12px;width:44px;height:44px;min-height:44px;padding:0;text-align:center;font-size:30px;line-height:44px}
      #mySidenav .yuyu-menu-divider{margin:12px 14px;border:0;border-top:1px solid var(--menu-line)}
      #menuOverlay.yuyu-menu-overlay{position:fixed;inset:0;width:100%;height:100%;z-index:12500;background:#0009;backdrop-filter:blur(2px);display:none}
      #menuOverlay.yuyu-menu-overlay.yuyu-open{display:block}
      .yuyu-menu-header a:focus-visible,.yuyu-menu-header button:focus-visible,#mySidenav.yuyu-menu-drawer a:focus-visible,#mySidenav.yuyu-menu-drawer button:focus-visible{outline:3px solid var(--menu-accent);outline-offset:2px}
      .yuyu-chapters{display:flex;flex-wrap:wrap;justify-content:center;gap:12px 24px;width:100%;box-sizing:border-box;padding:14px 18px;font:700 16px/1.6 'Zen Maru Gothic','Microsoft JhengHei',sans-serif}
      .yuyu-chapters a{color:inherit;text-decoration:underline;text-underline-offset:4px}
      @media(prefers-reduced-motion:reduce){#mySidenav.yuyu-menu-drawer{transition:none}}
    `;
    document.head.appendChild(style);

    const oldHeader = document.querySelector('.mobile-sticky-header,header.topbar');
    const cart = oldHeader && oldHeader.querySelector('.mobile-cart-btn');
    const chapters = oldHeader && oldHeader.querySelector('.betta-section-links');
    if (chapters) { chapters.className = 'yuyu-chapters'; oldHeader.after(chapters); }
    const header = document.createElement('header');
    header.className = 'yuyu-menu-header' + (warm ? ' yuyu-warm' : '');
    header.innerHTML = '<button type="button" class="hamburger-btn" aria-label="開啟選單" aria-controls="mySidenav" aria-expanded="false"><span class="bar"></span><span class="bar"></span><span class="bar"></span></button><a class="yuyu-brand">宇魚水族</a>';
    header.querySelector('a').href = url('index.html');
    if (cart) {
      header.appendChild(cart); // 移動原節點，保留購物車計數 ID 與原點擊行為。
      if (cart.tagName !== 'BUTTON') {
        cart.setAttribute('role', 'button'); cart.tabIndex = 0;
        cart.addEventListener('keydown', event => {
          if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); cart.click(); }
        });
      }
      cart.setAttribute('aria-label', '查看購物車');
    } else {
      const mark = document.createElement('img');
      mark.className = 'yuyu-mark'; mark.src = url('mark.png'); mark.alt = '';
      mark.onerror = () => { mark.style.visibility = 'hidden'; };
      header.appendChild(mark);
    }
    if (oldHeader) oldHeader.replaceWith(header); else document.body.prepend(header);
    const oldDrawer = document.getElementById('mySidenav');
    const oldOverlay = document.getElementById('menuOverlay');
    const drawer = document.createElement('aside');
    drawer.id = 'mySidenav'; drawer.className = 'yuyu-menu-drawer' + (warm ? ' yuyu-warm' : '');
    drawer.setAttribute('aria-label', '宇魚水族選單');
    drawer.setAttribute('aria-hidden', 'true'); drawer.setAttribute('inert', '');
    const close = document.createElement('button'); close.type = 'button';
    close.className = 'closebtn'; close.textContent = '×'; close.setAttribute('aria-label', '關閉選單');
    drawer.appendChild(close);
    const nav = document.createElement('nav'); nav.setAttribute('aria-label', '主要導覽'); drawer.appendChild(nav);
    const links = [
      ['index.html','🏠 回到首頁'],['about.html','📖 關於宇魚'],
      ['fish.html','🐠 活體專區'],['betta.html','🐟 鬥魚專區'],
      ['portfolio.html','📸 精選作品集'],['visit.html','📍 交通與來店指南']
    ];
    for (const [path, label] of links) {
      const a = document.createElement('a'); a.href = url(path); a.textContent = label;
      if (page === path) a.setAttribute('aria-current', 'page');
      nav.appendChild(a);
    }
    const divider = document.createElement('hr'); divider.className = 'yuyu-menu-divider'; nav.appendChild(divider);
    const extras = [
      ['https://myship.7-11.com.tw/general/detail/GM2312087898760','🛒 硬體與飼料'],
      ['https://myship.7-11.com.tw/general/detail/GM2404054052893','❄️ 冷凍豐年蝦'],
      [url('index.html#termsModal'),'📜 條款與細則','openTerms'],
      ['https://line.me/R/ti/p/@118rfvyo','💬 聯絡我們（官方 LINE）','openContactModal']
    ];
    for (const [href, label, action] of extras) {
      const a = document.createElement('a'); a.href = href; a.textContent = label;
      if (!action) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
      a.addEventListener('click', event => {
        if (action && typeof window[action] === 'function') {
          event.preventDefault(); window[action]();
        } else window.closeNav();
      });
      nav.appendChild(a);
    }
    const overlay = document.createElement('div'); overlay.id = 'menuOverlay';
    overlay.className = 'yuyu-menu-overlay'; overlay.setAttribute('aria-hidden', 'true');
    if (oldDrawer) oldDrawer.replaceWith(drawer); else document.body.appendChild(drawer);
    if (oldOverlay) oldOverlay.replaceWith(overlay); else document.body.appendChild(overlay);
    const trigger = header.querySelector('.hamburger-btn');
    let opened = false, oldOverflow = '';
    window.openNav = function () {
      if (opened) return;
      opened = true; oldOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      drawer.removeAttribute('inert'); drawer.setAttribute('aria-hidden', 'false');
      drawer.classList.add('yuyu-open'); overlay.classList.add('yuyu-open');
      trigger.setAttribute('aria-expanded', 'true'); close.focus();
    };
    window.closeNav = function (restoreFocus = true) {
      const wasOpened = opened;
      if (opened) document.body.style.overflow = oldOverflow;
      opened = false;
      if (restoreFocus && wasOpened) trigger.focus();
      drawer.classList.remove('yuyu-open'); overlay.classList.remove('yuyu-open');
      drawer.setAttribute('aria-hidden', 'true'); drawer.setAttribute('inert', '');
      trigger.setAttribute('aria-expanded', 'false');
    };
    trigger.addEventListener('click', window.openNav);
    close.addEventListener('click', () => window.closeNav());
    overlay.addEventListener('click', () => window.closeNav());
    document.addEventListener('keydown', event => {
      if (!opened) return;
      if (event.key === 'Escape') {
        event.preventDefault(); event.stopImmediatePropagation(); window.closeNav();
      }
      if (event.key === 'Tab') {
        const items = Array.from(drawer.querySelectorAll('a[href],button'));
        const first = items[0], last = items[items.length - 1];
        if (event.shiftKey && (document.activeElement === first || !drawer.contains(document.activeElement))) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || !drawer.contains(document.activeElement))) {
          event.preventDefault(); first.focus();
        }
      }
    }, true);
    const announcement = document.querySelector('.yuyu-announcement-bar');
    const measure = () => document.documentElement.style.setProperty('--yuyu-ann-height', (announcement ? announcement.getBoundingClientRect().height : 0) + 'px');
    measure(); document.body.classList.add('yuyu-menu-ready');
    window.addEventListener('resize', measure);
    if (announcement && typeof ResizeObserver !== 'undefined') new ResizeObserver(measure).observe(announcement);
    const openHash = () => {
      if (location.hash === '#termsModal' && typeof window.openTerms === 'function') window.openTerms();
    };
    window.addEventListener('hashchange', openHash); openHash();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
