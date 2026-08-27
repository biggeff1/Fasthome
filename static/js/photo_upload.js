/* Fasthome — sélection photo native et envoi multipart natif. */
(() => {
  'use strict';

  const MAX_PHOTOS_TOTAL = 40;
  const MAX_PHOTOS_PER_ZONE = 5;
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';

  function zoneOf(input) {
    return input.closest('[data-photo-zone]') || input.closest('.photo-slot') || input.parentElement;
  }

  function setFiles(input, files) {
    const dt = new DataTransfer();
    files.slice(0, MAX_PHOTOS_PER_ZONE).forEach((file) => dt.items.add(file));
    input.files = dt.files;
  }

  function preview(zone, files) {
    if (!zone) return;
    let counter = zone.querySelector('.fh-photo-counter');
    let grid = zone.querySelector('.fh-photo-preview');
    if (!counter) {
      counter = document.createElement('div');
      counter.className = 'fh-photo-counter';
      zone.appendChild(counter);
    }
    if (!grid) {
      grid = document.createElement('div');
      grid.className = 'fh-photo-preview';
      zone.appendChild(grid);
    }
    grid.replaceChildren();
    counter.textContent = files.length
      ? `${files.length}/${MAX_PHOTOS_PER_ZONE} photo${files.length > 1 ? 's' : ''} sélectionnée${files.length > 1 ? 's' : ''}`
      : 'Aucune photo sélectionnée';

    files.forEach((file) => {
      if (!file.type.startsWith('image/')) return;
      const item = document.createElement('div');
      item.className = 'fh-photo-item';
      const img = document.createElement('img');
      img.alt = file.name || 'Photo sélectionnée';
      img.loading = 'lazy';
      const url = URL.createObjectURL(file);
      img.src = url;
      img.onload = () => URL.revokeObjectURL(url);
      item.appendChild(img);
      grid.appendChild(item);
    });
  }

  function styles() {
    if (document.getElementById('fh-photo-upload-css')) return;
    const style = document.createElement('style');
    style.id = 'fh-photo-upload-css';
    style.textContent = `
      .fh-photo-preview{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}
      .fh-photo-item{aspect-ratio:1/1;overflow:hidden;border-radius:10px;background:#eef2f6;border:1px solid #dce3ea}
      .fh-photo-item img{width:100%;height:100%;object-fit:cover;display:block}
      .fh-photo-counter{margin-top:8px;color:#64707d;font-size:.82rem;font-weight:700}
      .fh-photo-input{position:absolute!important;width:1px!important;height:1px!important;opacity:0!important}
      .fh-photo-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
      .fh-photo-action{border:0;border-radius:12px;padding:12px 8px;background:#edf2f7;color:#18344d;font-weight:800;cursor:pointer}
    `;
    document.head.appendChild(style);
  }

  function addControls(form, input) {
    const zone = zoneOf(input);
    if (!zone || zone.querySelector('.fh-photo-actions')) return;

    const actions = document.createElement('div');
    actions.className = 'fh-photo-actions';

    const cameraInput = document.createElement('input');
    cameraInput.type = 'file';
    cameraInput.accept = 'image/*';
    cameraInput.capture = 'environment';
    cameraInput.multiple = false;
    cameraInput.hidden = true;
    cameraInput.setAttribute('aria-hidden', 'true');

    const camera = document.createElement('button');
    camera.type = 'button';
    camera.className = 'fh-photo-action';
    camera.textContent = '📷 Appareil photo';

    const picker = document.createElement('button');
    picker.type = 'button';
    picker.className = 'fh-photo-action';
    picker.textContent = '📁 Choisir un fichier';

    camera.addEventListener('click', () => {
      if (input.files.length >= MAX_PHOTOS_PER_ZONE) {
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);
        return;
      }
      cameraInput.click();
    });

    picker.addEventListener('click', () => input.click());

    cameraInput.addEventListener('change', () => {
      const file = cameraInput.files && cameraInput.files[0];
      cameraInput.value = '';
      if (!file) return;
      const files = [...input.files, file];
      if (files.length > MAX_PHOTOS_PER_ZONE) {
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);
        return;
      }
      setFiles(input, files);
      preview(zone, [...input.files]);
    });

    actions.append(camera, picker, cameraInput);
    input.parentNode.insertBefore(actions, input);
    const oldLabel = [...zone.querySelectorAll('label')].find((label) => label.htmlFor === input.id);
    if (oldLabel) oldLabel.style.display = 'none';
  }

  function bind(form, input) {
    if (input.dataset.fhPhotoBound === '1') return;
    input.dataset.fhPhotoBound = '1';
    input.multiple = true;
    input.accept = 'image/jpeg,image/png,image/webp';
    input.removeAttribute('capture');
    input.classList.add('fh-photo-input');
    addControls(form, input);

    input.addEventListener('change', () => {
      let files = [...input.files];
      if (files.length > MAX_PHOTOS_PER_ZONE) {
        files = files.slice(0, MAX_PHOTOS_PER_ZONE);
        setFiles(input, files);
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);
      }
      preview(zoneOf(input), [...input.files]);
    });

    preview(zoneOf(input), [...input.files]);
  }

  function install(form) {
    if (form.dataset.fhNativePhotosInstalled === '1') return;
    form.dataset.fhNativePhotosInstalled = '1';
    styles();
    const scan = () => {
      const inputs = [...form.querySelectorAll(INPUT_SELECTOR)];
      const total = inputs.reduce((sum, input) => sum + input.files.length, 0);
      if (total > MAX_PHOTOS_TOTAL) return;
      inputs.forEach((input) => bind(form, input));
    };
    scan();
    new MutationObserver(scan).observe(form, { childList: true, subtree: true });
    // IMPORTANT: aucune interception du submit, aucun canvas, aucun XHR.
    // Le navigateur envoie directement le multipart/form-data à Django.
  }

  function init() {
    document.querySelectorAll('form[enctype="multipart/form-data"]').forEach(install);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
