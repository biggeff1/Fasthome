/* Fasthome — upload mobile robuste : aucun aperçu ni traitement image côté navigateur. */
(() => {
  'use strict';
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';
  const ZONE_SELECTOR = '[data-photo-zone], .photo-slot';

  const zoneOf = input => input.closest(ZONE_SELECTOR) || input.parentElement;
  const allInputs = form => [...form.querySelectorAll(INPUT_SELECTOR)];

  function styles() {
    if (document.getElementById('fh-photo-upload-css')) return;
    const s = document.createElement('style');
    s.id = 'fh-photo-upload-css';
    s.textContent = `
      .fh-photo-input{position:absolute!important;width:1px!important;height:1px!important;opacity:0!important;pointer-events:none!important}
      .fh-photo-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
      .fh-photo-action{border:0;border-radius:12px;padding:13px 8px;background:#edf2f7;color:#18344d;font-weight:800;cursor:pointer;min-height:48px}
      .fh-photo-state{margin-top:10px;color:#18344d;font-size:.85rem;font-weight:800}
      .fh-photo-upload-status{display:none;margin-top:14px;padding:14px;border-radius:12px;background:#eaf4ff;color:#18344d;font-weight:800;text-align:center}
      .fh-photo-upload-status.is-visible{display:block}
      .fh-photo-upload-track{height:9px;margin-top:10px;border-radius:999px;background:#dbe5ee;overflow:hidden}
      .fh-photo-upload-bar{height:100%;width:0%;border-radius:999px;background:#163a5f;transition:width .15s ease}
      .fh-photo-upload-percent{display:block;margin-top:7px;font-size:.82rem;font-weight:900}
    `;
    document.head.appendChild(s);
  }

  function state(zone, text) {
    let n = zone.querySelector('.fh-photo-state');
    if (!n) { n = document.createElement('div'); n.className = 'fh-photo-state'; zone.appendChild(n); }
    n.textContent = text;
  }

  function hasPhoto(input) {
    return !!(input && input.files && input.files.length);
  }

  function cameraInput(original, zone) {
    const i = document.createElement('input');
    i.type = 'file';
    i.name = original.name;
    i.accept = 'image/*';
    i.capture = 'environment';
    i.multiple = false;
    i.className = 'fh-photo-input';
    i.addEventListener('change', () => {
      const file = i.files && i.files[0];
      if (!file) { i.remove(); return; }
      try {
        const dt = new DataTransfer();
        dt.items.add(file);
        original.files = dt.files;
        state(zone, '✓ Photo sélectionnée — prête à être téléversée');
      } catch (_) {
        state(zone, '✓ Photo sélectionnée — prête à être téléversée');
      }
      i.value = '';
      i.remove();
    }, {once:true});
    zone.appendChild(i);
    return i;
  }

  function controls(form, input) {
    const zone = zoneOf(input);
    if (!zone || zone.querySelector('.fh-photo-actions')) return;
    const actions = document.createElement('div');
    actions.className = 'fh-photo-actions';

    const camera = document.createElement('button');
    camera.type = 'button';
    camera.className = 'fh-photo-action';
    camera.textContent = '📷 Appareil photo';
    camera.addEventListener('click', () => {
      if (hasPhoto(input)) { state(zone, '✓ Une photo est déjà sélectionnée pour cette zone'); return; }
      cameraInput(input, zone).click();
    });

    const picker = document.createElement('button');
    picker.type = 'button';
    picker.className = 'fh-photo-action';
    picker.textContent = '📁 Choisir un fichier';
    picker.addEventListener('click', () => {
      if (hasPhoto(input)) { state(zone, '✓ Une photo est déjà sélectionnée pour cette zone'); return; }
      input.click();
    });

    actions.append(camera, picker);
    input.parentNode.insertBefore(actions, input);
    const label = [...zone.querySelectorAll('label')].find(x => x.htmlFor === input.id);
    if (label) label.style.display = 'none';
  }

  function bind(form, input) {
    if (input.dataset.fhPhotoBound === '1') return;
    input.dataset.fhPhotoBound = '1';
    input.multiple = false;
    input.removeAttribute('capture');
    input.accept = 'image/jpeg,image/png,image/webp,image/heic,image/heif';
    input.classList.add('fh-photo-input');
    controls(form, input);
    input.addEventListener('change', () => {
      if (hasPhoto(input)) state(zoneOf(input), '✓ Photo sélectionnée — prête à être téléversée');
    });
    state(zoneOf(input), 'Aucune photo sélectionnée');
  }

  function createStatus(form) {
    let status = form.querySelector('.fh-photo-upload-status');
    if (status) return status;
    status = document.createElement('div');
    status.className = 'fh-photo-upload-status';
    status.innerHTML = '<div class="fh-photo-upload-message"></div><div class="fh-photo-upload-track"><div class="fh-photo-upload-bar"></div></div><span class="fh-photo-upload-percent">0%</span>';
    form.appendChild(status);
    return status;
  }

  function submitProgress(form) {
    if (form.dataset.fhPhotoSubmitBound === '1') return;
    form.dataset.fhPhotoSubmitBound = '1';
    form.addEventListener('submit', () => {
      const count = allInputs(form).filter(hasPhoto).length;
      if (!count) return;
      const status = createStatus(form);
      status.classList.add('is-visible');
      status.querySelector('.fh-photo-upload-message').textContent = `⏳ Téléversement de ${count} photo${count > 1 ? 's' : ''}…`;
      status.querySelector('.fh-photo-upload-percent').textContent = 'Envoi en cours…';
    });
  }

  function init() {
    styles();
    document.querySelectorAll('form').forEach(form => {
      allInputs(form).forEach(input => bind(form, input));
      submitProgress(form);
    });
    new MutationObserver(() => {
      document.querySelectorAll('form').forEach(form => {
        allInputs(form).forEach(input => bind(form, input));
        submitProgress(form);
      });
    }).observe(document.body, {childList:true, subtree:true});
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
