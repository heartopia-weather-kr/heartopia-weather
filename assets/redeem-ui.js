/* Redeem-code UI is isolated from weather calculations and forecasts. */
(() => {
  'use strict';
  const button = document.getElementById('redeem-open');
  const dialog = document.getElementById('redeem-dialog');
  const list = document.getElementById('redeem-active');
  const expired = document.getElementById('redeem-expired');
  const expiredToggle = document.getElementById('redeem-expired-toggle');
  const dot = document.getElementById('redeem-dot');
  const message = document.getElementById('redeem-message');
  if (!button || !dialog) return;
  const storageKey = 'heartopia-redeem-seen-v1';
  let codes = [], seen = new Set(), newOnOpen = new Set(), loaded = false;
  const copiedUntil = new Map();
  let lastExpiredSignature = '';
  const normalized = value => String(value || '').trim().toLowerCase();
  const expiry = item => item.expiresAt ? Date.parse(item.expiresAt) : NaN;
  const isExpired = (item, now) => Number.isFinite(expiry(item)) && expiry(item) <= now;
  const isUnseen = item => !seen.has(normalized(item.code));
  const timeText = (item, now) => {
    const until = expiry(item) - now;
    if (!Number.isFinite(until)) return '만료일 미확인';
    if (until <= 0) return '만료';
    const date = new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(expiry(item)));
    if (until > 72 * 3600000) return '만료: ' + date + ' (KST)';
    if (until >= 24 * 3600000) return '만료 임박 · D-' + Math.ceil(until / 86400000) + ' · ' + date + ' (KST)';
    if (until >= 3600000) return '만료 임박 · ' + Math.floor(until / 3600000) + '시간 ' + Math.floor(until % 3600000 / 60000) + '분 남음';
    return '만료 임박 · ' + Math.floor(until / 60000) + '분 ' + Math.floor(until % 60000 / 1000) + '초 남음';
  };
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || '[]');
    if (Array.isArray(stored)) seen = new Set(stored.filter(x => typeof x === 'string'));
  } catch { /* Private browsing still permits viewing codes. */ }
  const save = () => { try { localStorage.setItem(storageKey, JSON.stringify([...seen])); } catch {} };
  const available = now => codes.filter(x => !isExpired(x, now));
  const confirmedAvailable = now => available(now).filter(x => Number.isFinite(expiry(x)));
  const updateDot = () => {
    dot.hidden = !loaded || !confirmedAvailable(Date.now()).some(isUnseen);
    button.setAttribute('aria-label', dot.hidden ? '리딤코드 열기' : '새 리딤코드 있음, 리딤코드 열기');
  };
  const node = (tag, cls, value) => {
    const element = document.createElement(tag);
    if (cls) element.className = cls;
    if (value !== undefined) element.textContent = value;
    return element;
  };
  const render = () => {
    const now = Date.now();
    const active = available(now).sort((a,b) => Number(newOnOpen.has(normalized(b.code))) - Number(newOnOpen.has(normalized(a.code))) || (Date.parse(b.postedAt) || 0) - (Date.parse(a.postedAt) || 0));
    const old = codes.filter(x => isExpired(x, now)).sort((a,b) => (Date.parse(b.postedAt) || 0) - (Date.parse(a.postedAt) || 0));
    lastExpiredSignature = codes.filter(x => isExpired(x,now)).map(x => normalized(x.code)).join('|');
    list.replaceChildren(); expired.replaceChildren();
    const build = (item, target, isNew) => {
      const card = node('article','redeem-code');
      const head = node('div','redeem-code-head');
      const name = node('strong','redeem-code-name',item.code);
      head.append(name);
      if (isNew) head.append(node('span','redeem-new','NEW'));
      const copy = node('button','redeem-copy','복사');
      copy.type = 'button'; copy.setAttribute('aria-label',item.code + ' 복사');
      if ((copiedUntil.get(normalized(item.code)) || 0) > Date.now()) copy.textContent = '✓ 복사됨';
      copy.addEventListener('click',async () => {
        try {
          await navigator.clipboard.writeText(item.code);
          copiedUntil.set(normalized(item.code),Date.now()+2000);
          copy.textContent = '✓ 복사됨';
          clearTimeout(copy._reset);
          copy._reset = setTimeout(() => { if (copy.isConnected) copy.textContent = '복사'; },2000);
        } catch { copy.textContent = '복사 실패'; copy._reset = setTimeout(() => { if(copy.isConnected) copy.textContent = '복사'; },2000); }
      });
      head.append(copy); card.append(head);
      if (item.rewards) card.append(node('p','redeem-rewards',item.rewards.replace(/,/g,' · ')));
      const expiryLabel = node('p','redeem-expiry',timeText(item,now));
      expiryLabel.dataset.code = normalized(item.code);
      card.append(expiryLabel);
      target.append(card);
    };
    active.forEach(item => build(item,list,newOnOpen.has(normalized(item.code))));
    old.forEach(item => build(item,expired,false));
    if (!active.length) list.append(node('p','redeem-empty','현재 표시할 사용 가능 코드가 없어요.'));
    if (!old.length) expired.append(node('p','redeem-empty','만료된 코드가 없어요.'));
    document.getElementById('redeem-active-count').textContent = String(active.length);
    document.getElementById('redeem-expired-count').textContent = String(old.length);
    updateDot();
  };
  async function load() {
    try {
      const response = await fetch('redeem-codes.json?t=' + Date.now(),{cache:'no-store'});
      if (!response.ok) throw new Error('데이터를 불러올 수 없어요.');
      const data = await response.json();
      if (!Array.isArray(data.codes)) throw new Error('코드 목록 형식이 올바르지 않아요.');
      codes = data.codes.filter(item => item && typeof item.code === 'string' && item.code.trim());
      loaded = true; message.hidden = true; updateDot();
      if (dialog.open) render();
      return true;
    } catch {
      message.textContent = '리딤코드 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.';
      message.hidden = false;
      return false;
    }
  }
  button.addEventListener('click',async () => {
    if (document.querySelector('dialog[open]')) return;
    if (!loaded) await load();
    if (loaded) {
      newOnOpen = new Set(available(Date.now()).filter(isUnseen).map(x => normalized(x.code)));
      render();
      newOnOpen.forEach(x => seen.add(x));
      save(); updateDot();
    } else { list.replaceChildren(); expired.replaceChildren(); }
    dialog.showModal();
  });
  document.getElementById('redeem-close').addEventListener('click',() => dialog.close());
  dialog.addEventListener('click',event => {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
  dialog.addEventListener('close',() => {
    newOnOpen.clear(); button.focus({preventScroll:true});
  });
  expiredToggle.addEventListener('click',() => {
    const open = expired.hidden;
    expired.hidden = !open;
    expiredToggle.setAttribute('aria-expanded',String(open));
  });
  load();
  setInterval(() => {
    if (!loaded) return;
    updateDot();
    if (!dialog.open) return;
    const now = Date.now();
    const signature = codes.filter(x => isExpired(x,now)).map(x => normalized(x.code)).join('|');
    if (signature !== lastExpiredSignature) { render(); return; }
    dialog.querySelectorAll('.redeem-expiry[data-code]').forEach(label => {
      const item = codes.find(x => normalized(x.code) === label.dataset.code);
      if (item) label.textContent = timeText(item,now);
    });
  },1000);
  setInterval(() => { if (!dialog.open) load(); },60000);
})();
