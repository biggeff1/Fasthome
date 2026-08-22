(() => {
  const MAX_PHOTOS = 50;
  const MAX_DIMENSION = 1920;
  const QUALITY = 0.82;

  function photoInputs(form) {
    return [...form.querySelectorAll('input[type="file"][name^="photos_"]')];
  }

  function normalizeInputs(form) {
    photoInputs(form).forEach((input) => {
      input.removeAttribute('multiple');
      input.accept = 'image/jpeg,image/png,image/webp';
    });
  }

  function sleep() {
    return new Promise((resolve) => setTimeout(resolve, 0));
  }

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
          ctx.drawImage(image, 0, 0, width, height);
          canvas.toBlob((blob) => {
            URL.revokeObjectURL(url);
            if (!blob) {
              reject(new Error('Impossible d’optimiser une image.'));
              return;
            }
            const stem = file.name.replace(/\.[^.]+$/, '') || 'photo';
            resolve(new File([blob], `${stem}.webp`, { type: 'image/webp', lastModified: Date.now() }));
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

  async function submitWithOptimizedPhotos(form, submitter) {
    if (form.dataset.photoUploading === '1') return;
    form.dataset.photoUploading = '1';

    const status = ensureStatus(form);
    const inputs = photoInputs(form);
    const selected = inputs.filter((input) => input.files && input.files.length);

    if (selected.length > MAX_PHOTOS) {
      throw new Error(`Maximum ${MAX_PHOTOS} photos par publication.`);
    }

    const statusText = (text) => {
      status.hidden = false;
      status.textContent = text;
    };

    statusText(selected.length ? `Préparation de ${selected.length} photo${selected.length > 1 ? 's' : ''}…` : 'Enregistrement…');

    const formData = new FormData(form, submitter || undefined);
    inputs.forEach((input) => formData.delete(input.name));

    for (let i = 0; i < selected.length; i += 1) {
      const input = selected[i];
      const file = input.files[0];
      statusText(`Optimisation des photos : ${i + 1}/${selected.length}`);
      const optimized = await compress(file);
      formData.append(input.name, optimized, optimized.name);
      // Yield to the browser so the page remains responsive with many images.
      await sleep();
    }

    statusText('Envoi des photos optimisées…');
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
      const submitter = event.submitter;
      try {
        await submitWithOptimizedPhotos(form, submitter);
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
