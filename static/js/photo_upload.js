/* Fasthome — upload photo mobile robuste et économe en mémoire. */
(() => {
  'use strict';

  const MAX_PHOTOS_TOTAL = 40;
  const MAX_PHOTOS_PER_ZONE = 5;
  const MAX_DIMENSION = 1600;
  const JPEG_QUALITY = 0.78;
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';
  const ZONE_SELECTOR = '[data-photo-zone], .photo-slot';

  const zoneOf = input => input.closest(ZONE_SELECTOR) || input.parentElement;
  const allPhotoInputs = form => [...form.querySelectorAll(INPUT_SELECTOR)];
  const filesInZone = zone => zone ? [...zone.querySelectorAll(INPUT_SELECTOR)].flatMap(i => [...i.files]) : [];
  const totalSelected = form => allPhotoInputs(form).reduce((n, i) => n + i.files.length, 0);

  function styles() {
    if (document.getElementById('fh-photo-upload-css')) return;
    const style = document.createElement('style');
    style.id = 'fh-photo-upload-css';
    style.textContent = `
      .fh-photo-preview{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}
      .fh-photo-item{position:relative;aspect-ratio:4/3;overflow:hidden;border-radius:12px;background:#eef2f6;border:1px solid #dce3ea}
      .fh-photo-item img{width:100%;height:100%;object-fit:cover;display:block}
      .fh-photo-name{position:absolute;left:4px;right:4px;bottom:4px;padding:4px 6px;border-radius:7px;background:rgba(0,0,0,.65);color:#fff;font-size:10px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
      .fh-photo-counter{margin-top:10px;color:#18344d;font-size:.85rem;font-weight:800}
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
    const files = filesInZone(zone).filter(f => f.type && f.type.startsWith('image/'));
    counter.textContent = files.length
      ? `✓ ${files.length}/${MAX_PHOTOS_PER_ZONE} photo${files.length > 1 ? 's' : ''} prête${files.length > 1 ? 's' : ''} à envoyer`
      : 'Aucune photo sélectionnée';
    files.forEach(file => {
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
    });
  }

  function canSelect(form, zone) {
    if (filesInZone(zone).length >= MAX_PHOTOS_PER_ZONE) {
      alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette pièce/zone.`);
      return false;
    }
    if (totalSelected(form) >= MAX_PHOTOS_TOTAL) {
      alert(`Maximum ${MAX_PHOTOS_TOTAL} photos pour ce logement.`);
      return false;
    }
    return true;
  }

  function createCameraInput(form, originalInput, zone) {
    const input = document.createElement('input');
    input.type = 'file';
    input.name = originalInput.name;
    input.accept = 'image/*';
    input.capture = 'environment';
    input.multiple = false;
    input.className = 'fh-photo-input';
    input.dataset.fhCameraInput = '1';
    input.addEventListener('change', () => {
      if (!input.files.length) { input.remove(); return; }
      if (filesInZone(zone).length > MAX_PHOTOS_PER_ZONE || totalSelected(form) > MAX_PHOTOS_TOTAL) {
        input.value = '';
        input.remove();
        alert('Nombre maximal de photos atteint.');
        return;
      }
      updatePreview(zone);
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
      if (!canSelect(form, zone)) return;
      createCameraInput(form, input, zone).click();
    });

    const picker = document.createElement('button');
    picker.type = 'button';
    picker.className = 'fh-photo-action';
    picker.textContent = '📁 Choisir un fichier';
    picker.addEventListener('click', () => {
      if (!canSelect(form, zone)) return;
      // Une seule photo à la fois : évite que le sélecteur Android manque de mémoire.
      input.multiple = false;
      input.click();
    });

    actions.append(camera, picker);
    input.parentNode.insertBefore(actions, input);
  }

  function bindInput(form, input) {
    if (input.dataset.fhPhotoBound === '1' || input.dataset.fhCameraInput === '1') return;
    input.dataset.fhPhotoBound = '1';
    input.multiple = false;
    input.accept = 'image/jpeg,image/png,image/webp';
    input.removeAttribute('capture');
    input.classList.add('fh-photo-input');
    addControls(form, input);

    input.addEventListener('change', () => {
      const zone = zoneOf(input);
      if (!input.files.length) return;
      if (filesInZone(zone).length > MAX_PHOTOS_PER_ZONE || totalSelected(form) > MAX_PHOTOS_TOTAL) {
        input.value = '';
        updatePreview(zone);
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos par zone et ${MAX_PHOTOS_TOTAL} photos par logement.`);
        return;
      }
      updatePreview(zone);
    });
    updatePreview(zoneOf(input));
  }

  function imageToCompressedFile(file) {
    return new Promise(resolve => {
      if (!file || !file.type.startsWith('image/')) return resolve(file);
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        try {
          const scale = Math.min(1, MAX_DIMENSION / Math.max(img.naturalWidth || 1, img.naturalHeight || 1));
          const width = Math.max(1, Math.round((img.naturalWidth || img.width) * scale));
          const height = Math.max(1, Math.round((img.naturalHeight || img.height) * scale));
          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d', { alpha: false });
          ctx.drawImage(img, 0, 0, width, height);
          canvas.toBlob(blob => {
            URL.revokeObjectURL(url);
            if (!blob) return resolve(file);
            const base = (file.name || 'photo').replace(/\.[^.]+$/, '');
            resolve(new File([blob], `${base}.jpg`, { type: 'image/jpeg', lastModified: Date.now() }));
          }, 'image/jpeg', JPEG_QUALITY);
        } catch (_) {
          URL.revokeObjectURL(url);
          resolve(file);
        }
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    });
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

  async function buildUploadForm(form, message) {
    const uploadForm = new FormData(form);
    const photoNames = new Set(allPhotoInputs(form).map(i => i.name));
    photoNames.forEach(name => uploadForm.delete(name));

    const photos = allPhotoInputs(form).flatMap(input => [...input.files].map(file => ({ name: input.name, file })));
    for (let i = 0; i < photos.length; i++) {
      message.textContent = `⏳ Optimisation de la photo ${i + 1}/${photos.length}…`;
      const compressed = await imageToCompressedFile(photos[i].file);
      uploadForm.append(photos[i].name, compressed, compressed.name || photos[i].file.name);
      // Libère le canvas et laisse le navigateur récupérer la mémoire entre les photos.
      await new Promise(requestAnimationFrame);
    }
    return uploadForm;
  }

  function addSubmitProgress(form) {
    if (form.dataset.fhUploadProgressBound === '1') return;
    form.dataset.fhUploadProgressBound = '1';

    form.addEventListener('submit', async event => {
      const count = totalSelected(form);
      if (!count) return;
      event.preventDefault();

      const status = createUploadStatus(form);
      const message = status.querySelector('.fh-photo-upload-message');
      const bar = status.querySelector('.fh-photo-upload-bar');
      const percent = status.querySelector('.fh-photo-upload-percent');
      status.classList.add('is-visible');
      bar.style.width = '0%';
      percent.textContent = '0%';

      try {
        const uploadForm = await buildUploadForm(form, message);
        message.textContent = `⏳ Téléversement de ${count} photo${count > 1 ? 's' : ''}…`;
        const xhr = new XMLHttpRequest();
        xhr.open(form.method || 'POST', form.action || window.location.href, true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.upload.addEventListener('progress', e => {
          if (!e.lengthComputable) return;
          const value = Math.min(100, Math.round((e.loaded / e.total) * 100));
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
      } catch (error) {
        console.error('Fasthome photo upload:', error);
        message.textContent = '⚠️ Impossible de préparer les photos. Réessayez avec une photo à la fois.';
        percent.textContent = 'Échec';
      }
    });
  }

  function install(form) {
    if (form.dataset.fhNativePhotosInstalled === '1') return;
    form.dataset.fhNativePhotosInstalled = '1';
    styles();
    addSubmitProgress(form);
    const scan = () => allPhotoInputs(form).forEach(input => bindInput(form, input));
    scan();
    new MutationObserver(scan).observe(form, { childList: true, subtree: true });
  }

  function init() {
    document.querySelectorAll('form[enctype="multipart/form-data"]').forEach(install);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
