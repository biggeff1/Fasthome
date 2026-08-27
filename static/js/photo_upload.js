/* Fasthome — upload photo mobile robuste, compression immédiate et appareil photo séparé. */
(() => {
  'use strict';

  const MAX_PHOTOS_TOTAL = 40;
  const MAX_PHOTOS_PER_ZONE = 5;
  const MAX_DIMENSION = 1280;
  const MAX_IMAGE_BYTES = 800_000;
  const QUALITY = 0.70;

  const photoInputs = (form) => [...form.querySelectorAll('input[type="file"][name^="photos_"]')];
  const getZone = (input) => input.closest('[data-photo-zone]') || input.closest('.photo-slot') || input.parentElement;

  function sleep() {
    return new Promise((resolve) => setTimeout(resolve, 0));
  }

  function canvasBlob(canvas, quality) {
    return new Promise((resolve, reject) => {
      const done = (blob) => blob ? resolve(blob) : reject(new Error('Impossible d’optimiser cette photo.'));
      if (typeof canvas.convertToBlob === 'function') {
        canvas.convertToBlob({ type: 'image/webp', quality }).then(done).catch(reject);
      } else {
        canvas.toBlob(done, 'image/webp', quality);
      }
    });
  }

  async function decodeImage(file) {
    if (typeof createImageBitmap === 'function') {
      try {
        const bitmap = await createImageBitmap(file, {
          imageOrientation: 'from-image',
          resizeWidth: MAX_DIMENSION,
          resizeHeight: MAX_DIMENSION,
          resizeQuality: 'high'
        });
        return bitmap;
      } catch (_) {
        try {
          const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
          return bitmap;
        } catch (_) {}
      }
    }

    const url = URL.createObjectURL(file);
    try {
      return await new Promise((resolve, reject) => {
        const img = new Image();
        img.decoding = 'async';
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error(`Image illisible : ${file.name}`));
        img.src = url;
      });
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function optimizePhoto(file) {
    if (!file || !file.type.startsWith('image/')) {
      throw new Error(`Fichier photo invalide : ${file?.name || 'inconnu'}.`);
    }

    if (file.size <= MAX_IMAGE_BYTES && file.type === 'image/webp') return file;

    const image = await decodeImage(file);
    try {
      const sw = image.width || image.naturalWidth;
      const sh = image.height || image.naturalHeight;
      if (!sw || !sh) throw new Error(`Image illisible : ${file.name}`);

      let scale = Math.min(1, MAX_DIMENSION / Math.max(sw, sh));
      let quality = QUALITY;
      let blob = null;

      for (let attempt = 0; attempt < 5; attempt += 1) {
        const width = Math.max(1, Math.round(sw * scale));
        const height = Math.max(1, Math.round(sh * scale));
        const canvas = typeof OffscreenCanvas === 'function'
          ? new OffscreenCanvas(width, height)
          : document.createElement('canvas');

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d', { alpha: false });
        if (!ctx) throw new Error('Canvas indisponible.');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(image, 0, 0, width, height);

        blob = await canvasBlob(canvas, quality);
        if (blob.size <= MAX_IMAGE_BYTES) break;

        scale *= 0.78;
        quality = Math.max(0.50, quality - 0.05);
        await sleep();
      }

      if (!blob) throw new Error(`Impossible d’optimiser ${file.name}.`);

      const stem = (file.name || 'photo').replace(/\.[^.]+$/, '') || 'photo';
      const optimized = new File([blob], `${stem}.webp`, {
        type: 'image/webp',
        lastModified: Date.now()
      });

      return optimized.size < file.size ? optimized : file;
    } finally {
      if (typeof image.close === 'function') image.close();
    }
  }

  function setInputFiles(input, files) {
    const dt = new DataTransfer();
    files.forEach((file) => dt.items.add(file));
    input.files = dt.files;
  }

  function renderPreview(zone, files) {
    if (!zone) return;

    let counter = zone.querySelector('.fh-photo-counter');
    let preview = zone.querySelector('.fh-photo-preview');

    if (!counter) {
      counter = document.createElement('div');
      counter.className = 'fh-photo-counter';
      zone.appendChild(counter);
    }
    if (!preview) {
      preview = document.createElement('div');
      preview.className = 'fh-photo-preview';
      zone.appendChild(preview);
    }

    preview.replaceChildren();
    counter.textContent = files.length
      ? `${files.length}/${MAX_PHOTOS_PER_ZONE} photo${files.length > 1 ? 's' : ''} prête${files.length > 1 ? 's' : ''}`
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
      preview.appendChild(item);
    });
  }

  function injectStyles() {
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
      .fh-photo-status{margin-top:8px;font-size:.82rem;font-weight:700}
    `;
    document.head.appendChild(style);
  }

  function ensureStatus(form) {
    let status = form.querySelector('[data-photo-upload-status]');
    if (!status) {
      status = document.createElement('div');
      status.dataset.photoUploadStatus = 'true';
      status.className = 'alert fh-photo-status';
      status.hidden = true;
      status.setAttribute('role', 'status');
      const actions = form.querySelector('.actions:last-of-type');
      if (actions) actions.before(status); else form.appendChild(status);
    }
    return status;
  }

  function csrfToken(form) {
    return form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
  }

  function uploadFormData(form, formData, status, total) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', form.action || window.location.href, true);
      xhr.withCredentials = true;
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      const token = csrfToken(form);
      if (token) xhr.setRequestHeader('X-CSRFToken', token);

      xhr.upload.addEventListener('progress', (event) => {
        status.textContent = event.lengthComputable
          ? `Envoi des photos : ${Math.round((event.loaded / event.total) * 100)}%`
          : `Envoi de ${total} photo${total > 1 ? 's' : ''}…`;
      });
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 400) {
          resolve(xhr.responseURL || window.location.href);
        } else {
          reject(new Error(`Le serveur a refusé l’envoi des photos (${xhr.status}).`));
        }
      });
      xhr.addEventListener('error', () => reject(new Error('Échec de l’envoi. Vérifiez votre connexion puis réessayez.')));
      xhr.addEventListener('abort', () => reject(new Error('Envoi interrompu.')));
      xhr.send(formData);
    });
  }

  async function prepareInput(input, status) {
    const original = [...(input.files || [])];
    if (!original.length) return [];
    if (original.length > MAX_PHOTOS_PER_ZONE) {
      throw new Error(`Maximum ${MAX_PHOTOS_PER_ZONE} photos par zone.`);
    }

    const optimized = [];
    for (let i = 0; i < original.length; i += 1) {
      status.hidden = false;
      status.textContent = `Préparation de la photo ${i + 1}/${original.length}…`;
      const file = await optimizePhoto(original[i]);
      optimized.push(file);
      await sleep();
    }

    setInputFiles(input, optimized);
    renderPreview(getZone(input), optimized);
    return optimized;
  }

  async function prepareAllPhotos(form, status) {
    const inputs = photoInputs(form);
    const total = inputs.reduce((sum, input) => sum + input.files.length, 0);
    if (total > MAX_PHOTOS_TOTAL) throw new Error(`Maximum ${MAX_PHOTOS_TOTAL} photos par logement.`);

    for (const input of inputs) await prepareInput(input, status);
    return total;
  }

  async function submitWithOptimizedPhotos(form, submitter) {
    if (form.dataset.photoUploading === '1') return;
    form.dataset.photoUploading = '1';
    const status = ensureStatus(form);

    try {
      const total = await prepareAllPhotos(form, status);
      const formData = new FormData(form, submitter || undefined);
      status.hidden = false;
      status.textContent = total ? `Envoi de ${total} photo${total > 1 ? 's' : ''}…` : 'Enregistrement…';
      const responseUrl = await uploadFormData(form, formData, status, total);
      window.location.assign(responseUrl);
    } finally {
      form.dataset.photoUploading = '0';
    }
  }

  function addActionButtons(form, input) {
    const zone = getZone(input);
    if (!zone || zone.querySelector('.fh-photo-actions')) return;

    const actions = document.createElement('div');
    actions.className = 'fh-photo-actions';

    const cameraInput = document.createElement('input');
    cameraInput.type = 'file';
    cameraInput.accept = 'image/*';
    cameraInput.setAttribute('capture', 'environment');
    cameraInput.multiple = false;
    cameraInput.hidden = true;
    cameraInput.setAttribute('aria-hidden', 'true');
    cameraInput.className = 'fh-camera-input';

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

    cameraInput.addEventListener('change', async () => {
      const file = cameraInput.files?.[0];
      cameraInput.value = '';
      if (!file) return;

      const current = [...(input.files || [])];
      if (current.length >= MAX_PHOTOS_PER_ZONE) {
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);
        return;
      }

      const status = ensureStatus(form);
      status.hidden = false;
      status.textContent = 'Optimisation de la photo…';

      try {
        const optimized = await optimizePhoto(file);
        setInputFiles(input, [...current, optimized]);
        renderPreview(zone, [...input.files]);
        status.hidden = true;
      } catch (error) {
        status.hidden = false;
        status.textContent = error?.message || 'Impossible de traiter la photo.';
      }
    });

    actions.append(camera, picker, cameraInput);
    input.parentNode.insertBefore(actions, input);

    const oldLabel = [...zone.querySelectorAll('label')].find((label) => label.htmlFor === input.id);
    if (oldLabel) oldLabel.style.display = 'none';
  }

  function bindInput(form, input) {
    if (input.dataset.fhPhotoBound === '1') return;
    input.dataset.fhPhotoBound = '1';
    input.multiple = true;
    input.accept = 'image/jpeg,image/png,image/webp';
    input.removeAttribute('capture');
    input.classList.add('fh-photo-input');

    addActionButtons(form, input);

    input.addEventListener('change', async () => {
      let files = [...(input.files || [])];
      if (files.length > MAX_PHOTOS_PER_ZONE) {
        files = files.slice(0, MAX_PHOTOS_PER_ZONE);
        setInputFiles(input, files);
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);
      }
      if (!files.length) {
        renderPreview(getZone(input), []);
        return;
      }

      const status = ensureStatus(form);
      status.hidden = false;
      status.textContent = `Préparation de ${files.length} photo${files.length > 1 ? 's' : ''}…`;

      try {
        await prepareInput(input, status);
        status.hidden = true;
      } catch (error) {
        status.hidden = false;
        status.textContent = error?.message || 'Impossible de préparer les photos.';
      }
    });

    renderPreview(getZone(input), [...input.files]);
  }

  function installUpload(form) {
    if (form.dataset.photoUploadInstalled === '1') return;
    form.dataset.photoUploadInstalled = '1';
    injectStyles();

    const bind = () => photoInputs(form).forEach((input) => bindInput(form, input));
    bind();

    const observer = new MutationObserver(bind);
    observer.observe(form, { childList: true, subtree: true });

    form.addEventListener('submit', async (event) => {
      if (form.dataset.photoUploading === '1') return;
      event.preventDefault();
      try {
        await submitWithOptimizedPhotos(form, event.submitter);
      } catch (error) {
        const status = ensureStatus(form);
        status.hidden = false;
        status.textContent = error?.message || 'Impossible d’enregistrer la publication.';
        form.dataset.photoUploading = '0';
      }
    });
  }

  function init() {
    document.querySelectorAll('form[enctype="multipart/form-data"]').forEach(installUpload);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
