/* Fasthome — téléversement photo mobile fiable. */
(() => {
  'use strict';

  const MAX_PHOTOS_TOTAL = 40;
  const MAX_PHOTOS_PER_ZONE = 5;
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';
  const ZONE_SELECTOR = '[data-photo-zone], .photo-slot';

  const zoneOf = (input) => input.closest(ZONE_SELECTOR) || input.parentElement;
  const allPhotoInputs = (form) => [...form.querySelectorAll(INPUT_SELECTOR)];
  const filesInZone = (zone) => zone ? [...zone.querySelectorAll(INPUT_SELECTOR)].flatMap(i => [...i.files]) : [];
  const totalSelected = (form) => allPhotoInputs(form).reduce((n, input) => n + input.files.length, 0);

  function styles() {
    if (document.getElementById('fh-photo-upload-css')) return;
    const style = document.createElement('style');
    style.id = 'fh-photo-upload-css';
    style.textContent = `
      .fh-photo-preview{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}
      .fh-photo-item{position:relative;aspect-ratio:4/3;overflow:hidden;border-radius:12px;background:#eef2f6;border:1px solid #dce3ea}
      .fh-photo-item img{width:100%;height:100%;object-fit:cover;display:block}
      .fh-photo-name{position:absolute;left:4px;right:4px;bottom:4px;padding:4px 6px;border-radius:7px;background:rgba(0,0,0,.65);color:#fff;font-size:10px;line-height:1.15;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
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
      @media(max-width:520px){.fh-photo-preview{grid-template-columns:1fr 1fr}.fh-photo-action{font-size:.82rem;padding:11px 5px}}
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
    const files = filesInZone(zone).filter(file => file.type.startsWith('image/'));
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

  function addCameraInput(form, originalInput, zone) {
    const cameraInput = document.createElement('input');
    cameraInput.type = 'file';
    cameraInput.name = originalInput.name;
    cameraInput.accept = 'image/*';
    cameraInput.capture = 'environment';
    cameraInput.multiple = false;
    cameraInput.className = 'fh-photo-input';
    cameraInput.dataset.fhCameraInput = '1';

    cameraInput.addEventListener('change', () => {
      if (!cameraInput.files.length) { cameraInput.remove(); return; }
      if (filesInZone(zone).length > MAX_PHOTOS_PER_ZONE) {
        cameraInput.value = '';
        cameraInput.remove();
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette pièce/zone.`);
        return;
      }
      if (totalSelected(form) > MAX_PHOTOS_TOTAL) {
        cameraInput.value = '';
        cameraInput.remove();
        alert(`Maximum ${MAX_PHOTOS_TOTAL} photos pour ce logement.`);
        return;
      }
      updatePreview(zone);
    });

    zone.appendChild(cameraInput);
    return cameraInput;
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
      addCameraInput(form, input, zone).click();
    });

    const picker = document.createElement('button');
    picker.type = 'button';
    picker.className = 'fh-photo-action';
    picker.textContent = '📁 Choisir un fichier';
    picker.addEventListener('click', () => {
      if (!canSelect(form, zone)) return;
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
    input.multiple = true;
    input.accept = 'image/jpeg,image/png,image/webp';
    input.classList.add('fh-photo-input');
    addControls(form, input);

    input.addEventListener('change', () => {
      const zone = zoneOf(input);
      const files = [...input.files];
      if (files.length > MAX_PHOTOS_PER_ZONE) {
        input.value = '';
        updatePreview(zone);
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette pièce/zone.`);
        return;
      }
      if (totalSelected(form) > MAX_PHOTOS_TOTAL) {
        input.value = '';
        updatePreview(zone);
        alert(`Maximum ${MAX_PHOTOS_TOTAL} photos pour ce logement.`);
        return;
      }
      updatePreview(zone);
    });

    updatePreview(zoneOf(input));
  }

  function csrfToken(form) {
    const tokenInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
    if (tokenInput?.value) return tokenInput.value;
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function createUploadStatus(form) {
    let status = form.querySelector('.fh-photo-upload-status');
    if (status) return status;
    status = document.createElement('div');
    status.className = 'fh-photo-upload-status';
    status.innerHTML = '<div class="fh-photo-upload-message">⏳ Préparation du téléversement…</div><div class="fh-photo-upload-track"><div class="fh-photo-upload-bar"></div></div><span class="fh-photo-upload-percent">0%</span>';
    form.appendChild(status);
    return status;
  }

  function addSubmitProgress(form) {
    if (form.dataset.fhUploadProgressBound === '1') return;
    form.dataset.fhUploadProgressBound = '1';

    form.addEventListener('submit', event => {
      const count = totalSelected(form);
      if (!count) return;
      event.preventDefault();

      const status = createUploadStatus(form);
      const message = status.querySelector('.fh-photo-upload-message');
      const bar = status.querySelector('.fh-photo-upload-bar');
      const percent = status.querySelector('.fh-photo-upload-percent');
      const submitter = event.submitter;

      status.classList.add('is-visible');
      message.textContent = `⏳ Téléversement de ${count} photo${count > 1 ? 's' : ''}…`;
      bar.style.width = '0%';
      percent.textContent = '0%';
      if (submitter) submitter.disabled = true;

      let data;
      try {
        data = new FormData(form, submitter || undefined);
      } catch (_) {
        data = new FormData(form);
        if (submitter?.name) data.append(submitter.name, submitter.value);
      }

      const xhr = new XMLHttpRequest();
      xhr.open(form.method || 'POST', form.action || window.location.href, true);
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      const csrf = csrfToken(form);
      if (csrf) xhr.setRequestHeader('X-CSRFToken', csrf);

      xhr.upload.addEventListener('progress', e => {
        if (!e.lengthComputable) return;
        const value = Math.min(100, Math.round((e.loaded / e.total) * 100));
        bar.style.width = `${value}%`;
        percent.textContent = `${value}%`;
        message.textContent = value < 100
          ? `⏳ Téléversement des photos… ${value}%`
          : '⏳ Photos reçues, enregistrement sur Fasthome…';
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 400) {
          bar.style.width = '100%';
          percent.textContent = '100%';
          message.textContent = '✓ Photos téléversées avec succès. Ouverture de la suite…';
          setTimeout(() => {
            window.location.href = xhr.responseURL || form.action || window.location.href;
          }, 300);
        } else {
          message.textContent = xhr.status === 403
            ? '⚠️ Sécurité CSRF refusée. Rechargez la page puis réessayez.'
            : '⚠️ Le téléversement a échoué. Vérifiez votre connexion puis réessayez.';
          bar.style.width = '0%';
          percent.textContent = 'Échec';
          if (submitter) submitter.disabled = false;
        }
      });

      xhr.addEventListener('error', () => {
        message.textContent = '⚠️ Impossible d’envoyer les photos. Vérifiez votre connexion.';
        bar.style.width = '0%';
        percent.textContent = 'Échec';
        if (submitter) submitter.disabled = false;
      });

      xhr.addEventListener('abort', () => {
        message.textContent = '⚠️ Téléversement interrompu.';
        bar.style.width = '0%';
        percent.textContent = 'Arrêté';
        if (submitter) submitter.disabled = false;
      });

      xhr.send(data);
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
