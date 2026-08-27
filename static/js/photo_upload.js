/* Fasthome — upload photo mobile robuste : 1 photo par zone, stockage IndexedDB et aperçus ultra-légers. */
(() => {
  'use strict';
  const MAX_DIMENSION = 1280;
  const THUMB_DIMENSION = 240;
  const JPEG_QUALITY = 0.68;
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';
  const ZONE_SELECTOR = '[data-photo-zone], .photo-slot';
  const DB_NAME = 'fasthome-photo-cache-v3';
  const STORE = 'photos';
  const preparedKeys = new WeakMap();
  let dbPromise;

  const zoneOf = input => input.closest(ZONE_SELECTOR) || input.parentElement;
  const allInputs = form => [...form.querySelectorAll(INPUT_SELECTOR)];

  function openDB() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      if (!('indexedDB' in window)) return reject(new Error('IndexedDB indisponible'));
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => { if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE); };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('Cache photo indisponible'));
    });
    return dbPromise;
  }

  async function dbPut(key, file) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(file, key);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error || new Error('Stockage photo impossible'));
    });
  }
  async function dbGet(key) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const req = db.transaction(STORE, 'readonly').objectStore(STORE).get(key);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error || new Error('Lecture photo impossible'));
    });
  }
  async function dbDelete(key) {
    if (!key) return;
    try {
      const db = await openDB();
      await new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).delete(key);
        tx.oncomplete = resolve;
        tx.onerror = () => reject(tx.error);
      });
    } catch (_) {}
  }

  function newKey() {
    return `${Date.now()}-${(crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2))}`;
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

  async function makeThumbnail(file) {
    let bitmap = null, canvas = null;
    try {
      bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
      const scale = Math.min(1, THUMB_DIMENSION / Math.max(bitmap.width || 1, bitmap.height || 1));
      canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round((bitmap.width || 1) * scale));
      canvas.height = Math.max(1, Math.round((bitmap.height || 1) * scale));
      const ctx = canvas.getContext('2d', { alpha: false });
      if (!ctx) throw new Error('Canvas indisponible');
      ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close(); bitmap = null;
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.62));
      canvas.width = 1; canvas.height = 1; canvas = null;
      return blob ? new File([blob], 'aperçu.jpg', { type: 'image/jpeg' }) : file;
    } finally {
      if (bitmap) { try { bitmap.close(); } catch (_) {} }
      if (canvas) { canvas.width = 1; canvas.height = 1; }
    }
  }

  async function compressImage(file) {
    if (!file || !file.type || !file.type.startsWith('image/')) return file;
    let bitmap = null, canvas = null;
    try {
      bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
      const sw = bitmap.width || 1, sh = bitmap.height || 1;
      const scale = Math.min(1, MAX_DIMENSION / Math.max(sw, sh));
      canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(sw * scale));
      canvas.height = Math.max(1, Math.round(sh * scale));
      const ctx = canvas.getContext('2d', { alpha: false });
      if (!ctx) throw new Error('Canvas indisponible');
      ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close(); bitmap = null;
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY));
      canvas.width = 1; canvas.height = 1; canvas = null;
      if (!blob) throw new Error('Compression impossible');
      const stem = (file.name || 'photo').replace(/\.[^.]+$/, '') || 'photo';
      return new File([blob], `${stem}.jpg`, { type: 'image/jpeg', lastModified: Date.now() });
    } finally {
      if (bitmap) { try { bitmap.close(); } catch (_) {} }
      if (canvas) { canvas.width = 1; canvas.height = 1; }
    }
  }

  async function storePrepared(input, compressed) {
    const key = newKey();
    await dbPut(key, compressed);
    preparedKeys.set(input, key);
    return key;
  }

  async function showPreview(zone, file) {
    if (!zone) return;
    let counter = zone.querySelector('.fh-photo-counter');
    let grid = zone.querySelector('.fh-photo-preview');
    if (!counter) { counter = document.createElement('div'); counter.className = 'fh-photo-counter'; zone.appendChild(counter); }
    if (!grid) { grid = document.createElement('div'); grid.className = 'fh-photo-preview'; zone.appendChild(grid); }
    grid.replaceChildren();
    counter.textContent = file ? '✓ Photo prête à envoyer' : 'Aucune photo sélectionnée';
    if (!file) return;
    const thumb = await makeThumbnail(file);
    const item = document.createElement('div'); item.className = 'fh-photo-item';
    const img = document.createElement('img'); img.alt = file.name || 'Photo sélectionnée';
    const url = URL.createObjectURL(thumb); img.src = url;
    img.onload = () => URL.revokeObjectURL(url);
    const name = document.createElement('span'); name.className = 'fh-photo-name'; name.textContent = file.name || 'Photo';
    item.append(img, name); grid.appendChild(item);
  }

  function canSelect(zone) {
    const input = zone?.querySelector('input[name^="photos_"]');
    if (input && (preparedKeys.has(input) || input.files.length)) {
      alert('Cette pièce/zone possède déjà sa photo. Une seule photo est autorisée par zone.');
      return false;
    }
    return true;
  }
  function processingMessage(zone, text) {
    let node = zone.querySelector('.fh-photo-processing');
    if (!node) { node = document.createElement('div'); node.className = 'fh-photo-processing'; zone.appendChild(node); }
    node.textContent = text; return node;
  }
  function removeProcessing(zone) { zone.querySelector('.fh-photo-processing')?.remove(); }

  async function acceptFile(input) {
    const zone = zoneOf(input);
    if (!zone || !input.files.length) return;
    if (!canSelect(zone)) { input.value = ''; return; }
    const original = input.files[0];
    processingMessage(zone, '⏳ Préparation de la photo…');
    try {
      const compressed = await compressImage(original);
      const key = await storePrepared(input, compressed);
      // Aucun original n'est conservé dans le DOM après cette ligne.
      input.value = '';
      await showPreview(zone, compressed);
      // La référence locale au fichier compressé disparaît à la fin de la fonction.
      void key;
    } catch (_) {
      input.value = '';
      alert('Impossible de préparer cette photo. Essayez une photo à la fois.');
    } finally { removeProcessing(zone); }
  }

  function createCameraInput(originalInput, zone) {
    const input = document.createElement('input');
    input.type = 'file'; input.accept = 'image/*'; input.capture = 'environment'; input.multiple = false;
    input.className = 'fh-photo-input'; input.dataset.fhCameraInput = '1';
    input.addEventListener('change', async () => {
      if (!input.files.length) { input.remove(); return; }
      if (!canSelect(zone)) { input.value = ''; input.remove(); return; }
      processingMessage(zone, '⏳ Préparation de la photo…');
      try {
        const compressed = await compressImage(input.files[0]);
        await storePrepared(originalInput, compressed);
        input.value = '';
        await showPreview(zone, compressed);
      } catch (_) {
        input.value = '';
        alert('Impossible de préparer cette photo. Essayez une photo à la fois.');
      } finally { input.remove(); removeProcessing(zone); }
    });
    zone.appendChild(input); return input;
  }

  function addControls(form, input) {
    const zone = zoneOf(input);
    if (!zone || zone.querySelector('.fh-photo-actions')) return;
    const actions = document.createElement('div'); actions.className = 'fh-photo-actions';
    const camera = document.createElement('button'); camera.type = 'button'; camera.className = 'fh-photo-action'; camera.textContent = '📷 Appareil photo';
    camera.addEventListener('click', () => { if (canSelect(zone)) createCameraInput(input, zone).click(); });
    const picker = document.createElement('button'); picker.type = 'button'; picker.className = 'fh-photo-action'; picker.textContent = '📁 Choisir un fichier';
    picker.addEventListener('click', () => { if (canSelect(zone)) { input.multiple = false; input.click(); } });
    actions.append(camera, picker); input.parentNode.insertBefore(actions, input);
    const oldLabel = [...zone.querySelectorAll('label')].find(label => label.htmlFor === input.id);
    if (oldLabel) oldLabel.style.display = 'none';
  }

  function bindInput(form, input) {
    if (input.dataset.fhPhotoBound === '1' || input.dataset.fhCameraInput === '1') return;
    input.dataset.fhPhotoBound = '1'; input.multiple = false;
    input.accept = 'image/jpeg,image/png,image/webp,image/heic,image/heif'; input.removeAttribute('capture'); input.classList.add('fh-photo-input');
    addControls(form, input); input.addEventListener('change', () => acceptFile(input));
    showPreview(zoneOf(input), null);
  }

  function createUploadStatus(form) {
    let status = form.querySelector('.fh-photo-upload-status');
    if (status) return status;
    status = document.createElement('div'); status.className = 'fh-photo-upload-status';
    status.innerHTML = '<div class="fh-photo-upload-message"></div><div class="fh-photo-upload-track"><div class="fh-photo-upload-bar"></div></div><span class="fh-photo-upload-percent">0%</span>';
    form.appendChild(status); return status;
  }

  async function buildUploadForm(form) {
    const uploadForm = new FormData(form);
    for (const input of allInputs(form)) uploadForm.delete(input.name);
    for (const input of allInputs(form)) {
      const key = preparedKeys.get(input);
      if (!key) continue;
      const file = await dbGet(key);
      if (file) uploadForm.append(input.name, file, file.name || `${input.name}.jpg`);
    }
    return uploadForm;
  }

  async function clearFormCache(form) {
    for (const input of allInputs(form)) {
      const key = preparedKeys.get(input);
      if (key) await dbDelete(key);
      preparedKeys.delete(input);
    }
  }

  function addSubmitProgress(form) {
    if (form.dataset.fhUploadProgressBound === '1') return;
    form.dataset.fhUploadProgressBound = '1';
    form.addEventListener('submit', async event => {
      const photos = allInputs(form).filter(input => preparedKeys.has(input));
      if (!photos.length) return;
      event.preventDefault();
      const status = createUploadStatus(form), message = status.querySelector('.fh-photo-upload-message'), bar = status.querySelector('.fh-photo-upload-bar'), percent = status.querySelector('.fh-photo-upload-percent');
      status.classList.add('is-visible'); bar.style.width = '0%'; percent.textContent = '0%'; message.textContent = `⏳ Téléversement de ${photos.length} photo${photos.length > 1 ? 's' : ''}…`;
      try {
        const uploadForm = await buildUploadForm(form);
        const xhr = new XMLHttpRequest(); xhr.open(form.method || 'POST', form.action || window.location.href, true); xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.upload.addEventListener('progress', e => { if (!e.lengthComputable) return; const value = Math.min(100, Math.round(e.loaded / e.total * 100)); bar.style.width = `${value}%`; percent.textContent = `${value}%`; message.textContent = value < 100 ? `⏳ Téléversement des photos… ${value}%` : '⏳ Photos envoyées, traitement par Fasthome…'; });
        xhr.addEventListener('load', async () => {
          if (xhr.status >= 200 && xhr.status < 400) { bar.style.width = '100%'; percent.textContent = '100%'; message.textContent = '✓ Photos téléversées. Ouverture de l’étape suivante…'; await clearFormCache(form); setTimeout(() => { window.location.href = xhr.responseURL || form.action || window.location.href; }, 250); }
          else { message.textContent = '⚠️ Le téléversement a échoué. Réessayez.'; percent.textContent = 'Échec'; }
        });
        xhr.addEventListener('error', () => { message.textContent = '⚠️ Impossible d’envoyer les photos. Vérifiez la connexion.'; percent.textContent = 'Échec'; });
        xhr.addEventListener('abort', () => { message.textContent = '⚠️ Téléversement interrompu.'; percent.textContent = 'Arrêté'; });
        xhr.send(uploadForm);
      } catch (_) { message.textContent = '⚠️ Impossible de préparer les photos. Réessayez une photo à la fois.'; percent.textContent = 'Échec'; }
    });
  }

  function install(form) {
    if (form.dataset.fhNativePhotosInstalled === '1') return;
    form.dataset.fhNativePhotosInstalled = '1'; styles(); addSubmitProgress(form);
    const scan = () => allInputs(form).forEach(input => bindInput(form, input));
    scan(); new MutationObserver(scan).observe(form, { childList: true, subtree: true });
  }
  function init() { document.querySelectorAll('form[enctype="multipart/form-data"]').forEach(install); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true }); else init();
})();
