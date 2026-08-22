/* Fasthome — upload photo non bloquant pour les publications. */
(() => {
  const MAX_PHOTOS_TOTAL = 40;
  const MAX_PHOTOS_PER_ZONE = 5;
  const MAX_DIMENSION = 1920;
  const QUALITY = 0.82;

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

  function compress(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => {
        try {
          const scale = Math.min(1, MAX_DIMENSION / Math.max(image.naturalWidth, image.naturalHeight));
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
          canvas.toBlob((blob) => {
            URL.revokeObjectURL(url);
            if (!blob) return reject(new Error('Impossible d’optimiser une image.'));
            const stem = file.name.replace(/\.[^.]+$/, '') || 'photo';
            // Si WebP n'est pas plus léger, on conserve l'original.
            resolve(blob.size < file.size
              ? new File([blob], `${stem}.webp`, { type: 'image/webp', lastModified: Date.now() })
              : file);
          }, 'image/webp', QUALITY);
        } catch (error) {
          URL.revokeObjectURL(url);
          reject(error);
        }
      };
      image.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error(`Image illisible : ${file.name}`));
      };
      image.src = url;
    });
  }

  function ensureStatus(form) {
    let status = form.querySelector('[data-photo-upload-status]');
    if (!status) {
      status = document.createElement('div');
      status.dataset.photoUploadStatus = 'true';
      status.className = 'alert';
      status.hidden = true;
      form.querySelector('.actions:last-of-type')?.before(status) || form.appendChild(status);
    }
    return status;
  }

  function selectedFiles(inputs) {
    return inputs.flatMap((input) => [...(input.files || [])]);
  }

  async function submitWithOptimizedPhotos(form, submitter) {
    if (form.dataset.photoUploading === '1') return;
    form.dataset.photoUploading = '1';

    const status = ensureStatus(form);
    const inputs = photoInputs(form);
    const filesByInput = inputs.map((input) => ({ input, files: [...(input.files || [])] }));
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
    status.textContent = total ? `Préparation de ${total} photo${total > 1 ? 's' : ''}…` : 'Enregistrement…';

    const formData = new FormData(form, submitter || undefined);
    inputs.forEach((input) => formData.delete(input.name));

    let done = 0;
    for (const item of filesByInput) {
      for (const file of item.files) {
        done += 1;
        status.textContent = `Optimisation des photos : ${done}/${total}`;
        const optimized = await compress(file);
        formData.append(item.input.name, optimized, optimized.name);
        // Rend la main au navigateur entre chaque image pour éviter de bloquer le téléphone.
        await sleep();
      }
    }

    status.textContent = total ? 'Envoi des photos optimisées…' : 'Enregistrement…';
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
