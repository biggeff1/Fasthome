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
