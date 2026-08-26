/* Fasthome — upload photo rapide et non bloquant pour les publications. */
(() => {
  // Keep client-side limits identical to the server-side publication policy.
  const MAX_PHOTOS_TOTAL = 50;
  const MAX_PHOTOS_PER_ZONE = 1;
  const MAX_DIMENSION = 1280;
  const QUALITY = 0.72;
  const MAX_IMAGE_BYTES = 800_000;
  const CONCURRENCY = 2;

  function photoInputs(form) {
    return [...form.querySelectorAll('input[type="file"][name^="photos_"]')];
  }

  function normalizeInputs(form) {
    photoInputs(form).forEach((input) => {
      input.multiple = true;
      input.accept = 'image/jpeg,image/png,image/webp';
    });
  }

  const sleep = () => new Promise((resolve) => setTimeout(resolve, 0));

  function canvasBlob(canvas, quality) {
    return new Promise((resolve, reject) => {
      const done = (blob) => blob
        ? resolve(blob)
        : reject(new Error('Impossible d’optimiser une image.'));
      if (typeof canvas.convertToBlob === 'function') {
        canvas.convertToBlob({ type: 'image/webp', quality }).then(done).catch(reject);
      } else {
        canvas.toBlob(done, 'image/webp', quality);
      }
    });
  }

  async function loadImage(file) {
    if (typeof createImageBitmap === 'function') {
      try {
        return await createImageBitmap(file, { imageOrientation: 'from-image' });
      } catch (_) {
        // Fallback for browsers that expose createImageBitmap but do not
        // support the requested image options.
      }
    }

    const url = URL.createObjectURL(file);
    try {
      return await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error(`Image illisible : ${file.name}`));
        img.src = url;
      });
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function compress(file) {
    if (file.size <= MAX_IMAGE_BYTES && file.type === 'image/webp') return file;

    const image = await loadImage(file);
    try {
      const sourceWidth = image.naturalWidth || image.width;
      const sourceHeight = image.naturalHeight || image.height;
      if (!sourceWidth || !sourceHeight) {
        throw new Error(`Image illisible : ${file.name}`);
      }

      let scale = Math.min(1, MAX_DIMENSION / Math.max(sourceWidth, sourceHeight));
      let quality = QUALITY;
      let blob = null;

      for (let attempt = 0; attempt < 6; attempt += 1) {
        const width = Math.max(1, Math.round(sourceWidth * scale));
        const height = Math.max(1, Math.round(sourceHeight * scale));

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

        const sizeRatio = Math.sqrt(MAX_IMAGE_BYTES / blob.size);
        scale *= Math.max(0.62, Math.min(0.86, sizeRatio * 0.90));
        quality = Math.max(0.50, quality - 0.05);
        await sleep();
      }

      if (!blob) throw new Error('Impossible d’optimiser une image.');

      const stem = file.name.replace(/\.[^.]+$/, '') || 'photo';
      const optimized = new File(
        [blob],
        `${stem}.webp`,
        { type: 'image/webp', lastModified: Date.now() },
      );

      if (file.size <= MAX_IMAGE_BYTES && file.size <= optimized.size) return file;
      return optimized;
    } finally {
      if (typeof image.close === 'function') image.close();
    }
  }

  function ensureStatus(form) {
    let status = form.querySelector('[data-photo-upload-status]');
    if (!status) {
      status = document.createElement('div');
      status.dataset.photoUploadStatus = 'true';
      status.className = 'alert';
      status.hidden = true;
      status.setAttribute('role', 'status');
      form.querySelector('.actions:last-of-type')?.before(status) || form.appendChild(status);
    }
    return status;
  }

  function uploadFormData(form, formData, status, total) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', form.action || window.location.href, true);
      xhr.withCredentials = true;
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

      xhr.upload.addEventListener('progress', (event) => {
        if (!event.lengthComputable) {
          status.textContent = `Envoi de ${total} photo${total > 1 ? 's' : ''}…`;
          return;
        }
        const percent = Math.round((event.loaded / event.total) * 100);
        status.textContent = `Envoi des photos : ${percent}% (${Math.ceil(event.loaded / 1_000_000)} / ${Math.ceil(event.total / 1_000_000)} Mo)`;
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 400) {
          resolve(xhr.responseURL || window.location.href);
          return;
        }
        const text = xhr.responseText || '';
        document.open();
        document.write(text);
        document.close();
        resolve(null);
      });

      xhr.addEventListener('error', () => reject(new Error('Échec de l’envoi des photos. Vérifiez votre connexion puis réessayez.')));
      xhr.addEventListener('abort', () => reject(new Error('Envoi des photos interrompu.')));
      xhr.send(formData);
    });
  }

  async function submitWithOptimizedPhotos(form, submitter) {
    if (form.dataset.photoUploading === '1') return;
    form.dataset.photoUploading = '1';

    const status = ensureStatus(form);
    const inputs = photoInputs(form);
    const filesByInput = inputs.map((input) => ({ input, files: [...(input.files || [])] }));
    const total = filesByInput.reduce((sum, item) => sum + item.files.length, 0);

    try {
      if (total > MAX_PHOTOS_TOTAL) {
        throw new Error(`Maximum ${MAX_PHOTOS_TOTAL} photos par logement.`);
      }
      for (const item of filesByInput) {
        if (item.files.length > MAX_PHOTOS_PER_ZONE) {
          throw new Error(`Maximum ${MAX_PHOTOS_PER_ZONE} photo pour chaque zone du logement.`);
        }
      }

      status.hidden = false;
      status.textContent = total ? `Préparation de ${total} photo${total > 1 ? 's' : ''}…` : 'Enregistrement…';

      const formData = new FormData(form, submitter || undefined);
      inputs.forEach((input) => formData.delete(input.name));

      const optimizedByInput = new Map();
      let completed = 0;
      const allFiles = filesByInput.flatMap((item) => item.files.map((file) => ({ input: item.input, file })));

      for (let start = 0; start < allFiles.length; start += CONCURRENCY) {
        const batch = allFiles.slice(start, start + CONCURRENCY);
        const results = await Promise.all(batch.map(async ({ input, file }) => {
          const optimized = await compress(file);
          completed += 1;
          status.textContent = `Optimisation des photos : ${completed}/${total}`;
          await sleep();
          return { input, optimized };
        }));

        results.forEach(({ input, optimized }) => {
          if (!optimizedByInput.has(input.name)) optimizedByInput.set(input.name, []);
          optimizedByInput.get(input.name).push(optimized);
        });
      }

      let optimizedTotal = 0;
      optimizedByInput.forEach((files, name) => {
        files.forEach((file) => {
          formData.append(name, file, file.name);
          optimizedTotal += file.size;
        });
      });

      status.textContent = total
        ? `Envoi de ${total} photo${total > 1 ? 's' : ''} (${Math.ceil(optimizedTotal / 1_000_000)} Mo)…`
        : 'Enregistrement…';

      const responseUrl = await uploadFormData(form, formData, status, total);
      if (responseUrl) window.location.assign(responseUrl);
    } finally {
      if (form.dataset.photoUploading === '1') form.dataset.photoUploading = '0';
    }
  }

  function install(form) {
    normalizeInputs(form);
    const observer = new MutationObserver(() => normalizeInputs(form));
    observer.observe(form, { childList: true, subtree: true });

    form.addEventListener('submit', async (event) => {
      if (form.dataset.photoUploading === '1') return;
      event.preventDefault();
      try {
        await submitWithOptimizedPhotos(form, event.submitter);
      } catch (error) {
        const status = ensureStatus(form);
        status.hidden = false;
        status.textContent = error?.message || 'Impossible de préparer les photos.';
        form.dataset.photoUploading = '0';
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form[enctype="multipart/form-data"]').forEach(install);
  });
})();

/* Fasthome — sélecteur photo mobile : Galerie ou Appareil photo. */
(() => {
  const STYLE_ID = 'fasthome-photo-picker-style';
  const MODAL_ID = 'fasthome-photo-picker';
  let bypassNextClick = false;
  let activeInput = null;

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      #${MODAL_ID}{position:fixed;inset:0;z-index:10000;display:none;align-items:flex-end;justify-content:center;background:rgba(10,25,40,.48);padding:16px}
      #${MODAL_ID}.is-open{display:flex}
      .fh-photo-sheet{width:min(100%,440px);background:#fff;border-radius:20px;padding:18px;box-shadow:0 18px 50px rgba(0,0,0,.25);animation:fhPhotoSheetIn .18s ease-out}
      .fh-photo-sheet h3{margin:0 0 5px;color:#18344d;font-size:1.08rem}
      .fh-photo-sheet p{margin:0 0 15px;color:#6d7782;font-size:.84rem}
      .fh-photo-options{display:grid;grid-template-columns:1fr 1fr;gap:10px}
      .fh-photo-option{min-height:82px;border:1px solid #dfe5eb;border-radius:14px;background:#f7f9fb;color:#18344d;font-weight:800;cursor:pointer;font-size:.88rem}
      .fh-photo-option span{display:block;font-size:1.65rem;margin-bottom:5px}
      .fh-photo-cancel{width:100%;margin-top:10px;border:0;background:transparent;color:#6d7782;padding:10px;cursor:pointer;font-weight:700}
      @keyframes fhPhotoSheetIn{from{transform:translateY(18px);opacity:.4}to{transform:translateY(0);opacity:1}}
    `;
    document.head.appendChild(style);
  }

  function ensureModal() {
    let modal = document.getElementById(MODAL_ID);
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Choisir une source pour la photo');
    modal.innerHTML = `
      <div class="fh-photo-sheet">
        <h3>Ajouter une photo</h3>
        <p>Choisissez comment ajouter la photo de ce logement.</p>
        <div class="fh-photo-options">
          <button type="button" class="fh-photo-option" data-photo-choice="gallery"><span>🖼️</span>Choisir dans la galerie</button>
          <button type="button" class="fh-photo-option" data-photo-choice="camera"><span>📷</span>Prendre une photo</button>
        </div>
        <button type="button" class="fh-photo-cancel" data-photo-choice="cancel">Annuler</button>
      </div>`;
    document.body.appendChild(modal);

    modal.addEventListener('click', (event) => {
      if (event.target === modal) closePicker();
      const choice = event.target.closest('[data-photo-choice]')?.dataset.photoChoice;
      if (!choice) return;
      if (choice === 'cancel') {
        closePicker();
        return;
      }
      chooseSource(choice);
    });
    return modal;
  }

  function closePicker() {
    document.getElementById(MODAL_ID)?.classList.remove('is-open');
    activeInput = null;
  }

  function chooseSource(source) {
    const input = activeInput;
    if (!input) return;

    const previousCapture = input.getAttribute('capture');
    bypassNextClick = true;
    if (source === 'camera') input.setAttribute('capture', 'environment');
    else input.removeAttribute('capture');

    closePicker();
    input.click();

    window.setTimeout(() => {
      bypassNextClick = false;
      if (previousCapture === null) input.removeAttribute('capture');
      else input.setAttribute('capture', previousCapture);
    }, 400);
  }

  function showPicker(input) {
    activeInput = input;
    ensureStyle();
    const modal = ensureModal();
    modal.classList.add('is-open');
  }

  function updatePhotoCount(input) {
    const wrapper = input.closest('.photo-slot');
    const count = wrapper?.querySelector('.photo-count');
    if (!count) return;
    const total = input.files?.length || 0;
    count.textContent = total
      ? `${total} photo${total > 1 ? 's' : ''} sélectionnée${total > 1 ? 's' : ''}`
      : 'Aucune photo sélectionnée';
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('click', (event) => {
      const input = event.target.closest('input[type="file"][name^="photos_"]');
      if (!input) return;
      if (bypassNextClick) return;
      event.preventDefault();
      event.stopPropagation();
      showPicker(input);
    }, true);

    document.addEventListener('change', (event) => {
      const input = event.target.closest('input[type="file"][name^="photos_"]');
      if (input) updatePhotoCount(input);
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closePicker();
    });
  });
})();
