/* Fasthome — photos mobiles : 1 photo par zone, traitement léger et sans accumulation des originaux. */
(() => {
  'use strict';

  const MAX_PER_ZONE = 1;
  const MAX_DIMENSION = 1280;
  const JPEG_QUALITY = 0.68;
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';
  const ZONE_SELECTOR = '[data-photo-zone], .photo-slot';
  const preparedFiles = new WeakMap();

  const zoneOf = input => input.closest(ZONE_SELECTOR) || input.parentElement;
  const allInputs = form => [...form.querySelectorAll(INPUT_SELECTOR)];

  function zonePrepared(zone) {
    const input = zone?.querySelector(`input[name^="photos_"]`);
    return input ? preparedFiles.get(input) || null : null;
  }

  function styles() {
    if (document.getElementById('fh-photo-upload-css')) return;
    const style = document.createElement('style');
    style.id = 'fh-photo-upload-css';
    style.textContent = `
      .fh-photo-preview{display:grid;grid-template-columns:1fr;gap:8px;margin-top:12px}
      .fh-photo-item{position:relative;aspect-ratio:4/3;overflow:hidden;border-radius:12px;background:#eef2f6;border:1px solid #dce3ea}
      .fh-photo-item img{width:100%;height:100%;object-fit:cover;display:block}
      .fh-photo-name{position:absolute;left:4px;right:4px;bottom:4px;padding:4px 6px;border-radius:7px;background:rgba(0,0,0,.65);color:#fff;font-size:10px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
      .fh-photo-counter{margin-top:10px;color:#18344d;font-size:.85rem;font-weight:800}
      .fh-photo-processing{margin-top:10px;padding:10px;border-radius:10px;background:#edf5ff;color:#18344d;font-size:.82rem;font-weight:800;text-align:center}
      .fh-photo-input{position:absolute!important;width:1px!important;height:1px!important;opacity:0!important;pointer-events:none!important}
      .fh-photo-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
      .fh-photo-action{border:0;border-radius:12px;padding:13px 8px;background:#edf2f7;color:#18344d;font-weight:800;cursor:pointer;min-height:48px}
      .fh-photo-action:active{transform:scale(.98)}
      .fh-photo-upload-status{display:none;margin-top:14px;padding:14px;border-radius:12px;background:#eaf4ff;color:#18344d;font-weight:800;text-align:center}
      .fh-photo-upload-status.is-visible{display:block}
      .fh-photo-upload-track{height:9px;margin-top:10px;border-radius:999px;background:#dbe5ee;overflow:hidden}
      .fh-photo-upload-bar{height:100%;width:0%;border-radius:999px;background:#163a5f;transition:width .15s ease}
      .fh-photo-upload-percent{display:block;margin-top:7px;font-size:.82rem;font-weight:900}
    `;
    document.head.appendChild(style);
  }

  function updatePreview(zone) {
    if (!zone) return;
    let counter = zone.querySelector('.fh-photo-counter');
    let grid = zone.querySelector('.fh-photo-preview');
    if (!counter) { counter = document.createElement('div'); counter.className = 'fh-photo-counter'; zone.appendChild(counter); }
    if (!grid) { grid = document.createElement('div'); grid.className = 'fh-photo-preview'; zone.appendChild(grid); }
    grid.replaceChildren();
    const input = zone.querySelector(`input[name^="photos_"]`);
    const file = input ? (preparedFiles.get(input) || input.files[0] || null) : null;
    counter.textContent = file ? '✓ Photo prête à envoyer' : 'Aucune photo sélectionnée';
    if (!file) return;
    const item = document.createElement('div');
    item.className = 'fh-photo-item';
    const img = document.createElement('img');
    img.alt = file.name || 'Photo sélectionnée';
    const url = URL.createObjectURL(file);
    img.src = url;
    img.onload = () => URL.revokeObjectURL(url);
    const name = document.createElement('span');
    name.className = 'fh-photo-name';
    name.textContent = file.name || 'Photo';
    item.append(img, name);
    grid.appendChild(item);
  }

  function canSelect(zone) {
    if (!zone) return false;
    const input = zone.querySelector(`input[name^="photos_"]`);
    if (input && (preparedFiles.has(input) || input.files.length)) {
      alert('Cette pièce/zone possède déjà sa photo. Une seule photo est autorisée par zone.');
      return false;
    }
    return true;
  }

  function processingMessage(zone, text) {
    let node = zone.querySelector('.fh-photo-processing');
    if (!node) { node = document.createElement('div'); node.className = 'fh-photo-processing'; zone.appendChild(node); }
    node.textContent = text;
    return node;
  }

  function removeProcessing(zone) { zone.querySelector('.fh-photo-processing')?.remove(); }

  async function compressImage(file) {
    if (!file || !file.type || !file.type.startsWith('image/')) return file;
    // Les très gros fichiers sont traités par le navigateur une seule fois,
    // puis l'input natif est vidé immédiatement. Aucun original ne reste attaché au formulaire.
    const url = URL.createObjectURL(file);
    try {
      const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
      const sw = bitmap.width || 1;
      const sh = bitmap.height || 1;
      const scale = Math.min(1, MAX_DIMENSION / Math.max(sw, sh));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(sw * scale));
      canvas.height = Math.max(1, Math.round(sh * scale));
      const ctx = canvas.getContext('2d', { alpha: false });
      if (!ctx) throw new Error('Canvas indisponible');
      ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close();
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY));
      canvas.width = 1;
      canvas.height = 1;
      if (!blob) return file;
      const stem = (file.name || 'photo').replace(/\.[^.]+$/, '') || 'photo';
      return new File([blob], `${stem}.jpg`, { type: 'image/jpeg', lastModified: Date.now() });
    } catch (_) {
      return file;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function acceptFile(input) {
    const zone = zoneOf(input);
    if (!zone || !input.files.length) return;
    if (!canSelect(zone)) { input.value = ''; return; }

    const original = input.files[0];
    processingMessage(zone, '⏳ Préparation de la photo…');

    try {
      const compressed = await compressImage(original);
      // Point essentiel : on retire immédiatement le fichier original du champ natif.
      input.value = '';
      preparedFiles.set(input, compressed);
      updatePreview(zone);
    } finally {
      removeProcessing(zone);
    }
  }

  function createCameraInput(originalInput, zone) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    input.multiple = false;
    input.className = 'fh-photo-input';
    input.dataset.fhCameraInput = '1';
    input.addEventListener('change', async () => {
      if (!input.files.length) { input.remove(); return; }
      if (!canSelect(zone)) { input.remove(); return; }
      processingMessage(zone, '⏳ Préparation de la photo…');
      try {
        const compressed = await compressImage(input.files[0]);
        // Le champ caméra temporaire est détruit : il ne reste aucune référence native au fichier original.
        input.value = '';
        preparedFiles.set(originalInput, compressed);
        updatePreview(zone);
      } finally {
        input.remove();
        removeProcessing(zone);
      }
    });
    zone.appendChild(input);
    return input;
  }

  function addControls(form, input) {
    const zone = zoneOf(input);
    if (!zone || zone.querySelector('.fh-photo-actions')) return;
    const actions = document.createElement('div');
    actions.className = 'fh-photo-actions';

    const camera = document.createElement('button');
    camera.type = 'button';
    camera.className = 'fh-photo-action';
    camera.textContent = '📷 Appareil photo';
    camera.addEventListener('click', () => {
      if (!canSelect(zone)) return;
      createCameraInput(input, zone).click();
    });

    const picker = document.createElement('button');
    picker.type = 'button';
    picker.className = 'fh-photo-action';
    picker.textContent = '📁 Choisir un fichier';
    picker.addEventListener('click', () => {
      if (!canSelect(zone)) return;
      input.multiple = false;
      input.click();
    });

    actions.append(camera, picker);
    input.parentNode.insertBefore(actions, input);
    const oldLabel = [...zone.querySelectorAll('label')].find(label => label.htmlFor === input.id);
    if (oldLabel) oldLabel.style.display = 'none';
  }

  function bindInput(form, input) {
    if (input.dataset.fhPhotoBound === '1' || input.dataset.fhCameraInput === '1') return;
    input.dataset.fhPhotoBound = '1';
    input.multiple = false;
    input.accept = 'image/jpeg,image/png,image/webp,image/heic,image/heif';
    input.removeAttribute('capture');
    input.classList.add('fh-photo-input');
    addControls(form, input);
    input.addEventListener('change', () => acceptFile(input));
    updatePreview(zoneOf(input));
  }

  function createUploadStatus(form) {
    let status = form.querySelector('.fh-photo-upload-status');
    if (status) return status;
    status = document.createElement('div');
    status.className = 'fh-photo-upload-status';
    status.innerHTML = '<div class="fh-photo-upload-message"></div><div class="fh-photo-upload-track"><div class="fh-photo-upload-bar"></div></div><span class="fh-photo-upload-percent">0%</span>';
    form.appendChild(status);
    return status;
  }

  function addSubmitProgress(form) {
    if (form.dataset.fhUploadProgressBound === '1') return;
    form.dataset.fhUploadProgressBound = '1';
    form.addEventListener('submit', event => {
      const inputs = allInputs(form);
      const photos = inputs.map(input => ({ input, file: preparedFiles.get(input) })).filter(x => x.file);
      if (!photos.length) return;
      event.preventDefault();

      const status = createUploadStatus(form);
      const message = status.querySelector('.fh-photo-upload-message');
      const bar = status.querySelector('.fh-photo-upload-bar');
      const percent = status.querySelector('.fh-photo-upload-percent');
      status.classList.add('is-visible');
      bar.style.width = '0%';
      percent.textContent = '0%';

      const uploadForm = new FormData(form);
      inputs.forEach(input => uploadForm.delete(input.name));
      photos.forEach(({ input, file }) => uploadForm.append(input.name, file, file.name));

      message.textContent = `⏳ Téléversement de ${photos.length} photo${photos.length > 1 ? 's' : ''}…`;
      const xhr = new XMLHttpRequest();
      xhr.open(form.method || 'POST', form.action || window.location.href, true);
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.upload.addEventListener('progress', e => {
        if (!e.lengthComputable) return;
        const value = Math.min(100, Math.round(e.loaded / e.total * 100));
        bar.style.width = `${value}%`;
        percent.textContent = `${value}%`;
        message.textContent = value < 100 ? `⏳ Téléversement des photos… ${value}%` : '⏳ Photos envoyées, traitement par Fasthome…';
      });
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 400) {
          bar.style.width = '100%';
          percent.textContent = '100%';
          message.textContent = '✓ Photos téléversées. Ouverture de l’étape suivante…';
          setTimeout(() => { window.location.href = xhr.responseURL || form.action || window.location.href; }, 250);
        } else {
          message.textContent = '⚠️ Le téléversement a échoué. Réessayez.';
          percent.textContent = 'Échec';
        }
      });
      xhr.addEventListener('error', () => { message.textContent = '⚠️ Impossible d’envoyer les photos. Vérifiez la connexion.'; percent.textContent = 'Échec'; });
      xhr.addEventListener('abort', () => { message.textContent = '⚠️ Téléversement interrompu.'; percent.textContent = 'Arrêté'; });
      xhr.send(uploadForm);
    });
  }

  function install(form) {
    if (form.dataset.fhNativePhotosInstalled === '1') return;
    form.dataset.fhNativePhotosInstalled = '1';
    styles();
    addSubmitProgress(form);
    const scan = () => allInputs(form).forEach(input => bindInput(form, input));
    scan();
    new MutationObserver(scan).observe(form, { childList: true, subtree: true });
  }

  function init() {
    document.querySelectorAll('form[enctype="multipart/form-data"]').forEach(install);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();