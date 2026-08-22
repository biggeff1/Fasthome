/* Fasthome — upload photo rapide et non bloquant pour les publications. */
(() => {
  const MAX_PHOTOS_TOTAL = 40;
  const MAX_PHOTOS_PER_ZONE = 5;
  const MAX_DIMENSION = 1600;
  const QUALITY = 0.74;
  const MAX_IMAGE_BYTES = 1_000_000;
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
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error('Impossible d’optimiser une image.'));
      }, 'image/webp', quality);
    });
  }

  async function compress(file) {
    // Une petite image déjà légère ne mérite pas d’être retraitée.
    if (file.size <= MAX_IMAGE_BYTES && file.type === 'image/webp') return file;

    const url = URL.createObjectURL(file);
    try {
      const image = await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error(`Image illisible : ${file.name}`));
        img.src = url;
      });

      let scale = Math.min(
        1,
        MAX_DIMENSION / Math.max(image.naturalWidth, image.naturalHeight),
      );
      let quality = QUALITY;
      let blob = null;

      // On vise ~1 Mo maximum par photo pour que plusieurs photos
      // restent envoyables sur mobile sans dépasser les limites HTTP.
      for (let attempt = 0; attempt < 5; attempt += 1) {
        const width = Math.max(1, Math.round(image.naturalWidth * scale));
        const height = Math.max(1, Math.round(image.naturalHeight * scale));
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d', { alpha: false });
        if (!ctx) throw new Error('Canvas indisponible.');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(image, 0, 0, width, height);

        blob = await canvasBlob(canvas, quality);
        if (blob.size <= MAX_IMAGE_BYTES) break;

        // Réduit progressivement la résolution et la qualité uniquement
        // pour les photos encore trop lourdes.
        const sizeRatio = Math.sqrt(MAX_IMAGE_BYTES / blob.size);
        scale *= Math.max(0.68, Math.min(0.88, sizeRatio * 0.92));
        quality = Math.max(0.55, quality - 0.05);
        await sleep();
      }

      if (!blob) throw new Error('Impossible d’optimiser une image.');

      const stem = file.name.replace(/\.[^.]+$/, '') || 'photo';
      const optimized = new File(
        [blob],
        `${stem}.webp`,
        { type: 'image/webp', lastModified: Date.now() },
      );

      // Si l’original est déjà plus petit et sous la limite, il est inutile
      // de le convertir.
      if (file.size <= MAX_IMAGE_BYTES && file.size <= optimized.size) return file;
      return optimized;
    } finally {
      URL.revokeObjectURL(url);
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

  async function submitWithOptimizedPhotos(form, submitter) {
    if (form.dataset.photoUploading === '1') return;
    form.dataset.photoUploading = '1';

    const status = ensureStatus(form);
    const inputs = photoInputs(form);
    const filesByInput = inputs.map((input) => ({
      input,
      files: [...(input.files || [])],
    }));
    const total = filesByInput.reduce((sum, item) => sum + item.files.length, 0);

    if (total > MAX_PHOTOS_TOTAL) {
      throw new Error(`Maximum ${MAX_PHOTOS_TOTAL} photos par logement.`);
    }

    for (const item of filesByInput) {
      if (item.files.length > MAX_PHOTOS_PER_ZONE) {
        throw new Error(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour chaque zone du logement.`);
      }
    }

    status.hidden = false;
    status.textContent = total
      ? `Préparation de ${total} photo${total > 1 ? 's' : ''}…`
      : 'Enregistrement…';

    const formData = new FormData(form, submitter || undefined);
    inputs.forEach((input) => formData.delete(input.name));

    const optimizedByInput = new Map();
    let completed = 0;
    const allFiles = filesByInput.flatMap((item) =>
      item.files.map((file) => ({ input: item.input, file }))
    );

    // Deux conversions simultanées : nettement plus rapide, tout en évitant
    // de saturer la mémoire des téléphones modestes.
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

    const response = await fetch(form.action || window.location.href, {
      method: 'POST',
      body: formData,
      credentials: 'same-origin',
      redirect: 'follow',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });

    if (!response.ok) {
      const text = await response.text();
      document.open();
      document.write(text);
      document.close();
      return;
    }

    window.location.assign(response.url || window.location.href);
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
