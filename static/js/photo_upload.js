/* Fasthome — upload photo mobile robuste.
 *
 * Principe :
 * - La galerie utilise directement l'input file du formulaire.
 * - Chaque photo prise avec l'appareil possède son propre input file.
 * - Aucun DataTransfer, aucun canvas, aucun XHR/fetch.
 * - Toutes les photos restent donc réellement attachées au multipart/form-data
 *   envoyé par le navigateur à Django.
 */
(() => {
  'use strict';

  const MAX_PHOTOS_TOTAL = 40;
  const MAX_PHOTOS_PER_ZONE = 5;
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';
  const ZONE_SELECTOR = '[data-photo-zone], .photo-slot';

  function zoneOf(input) {
    return input.closest(ZONE_SELECTOR) || input.parentElement;
  }

  function allPhotoInputs(form) {
    return [...form.querySelectorAll(INPUT_SELECTOR)];
  }

  function filesInZone(zone) {
    if (!zone) return [];
    return [...zone.querySelectorAll('input[type="file"][name^="photos_"]')]
      .flatMap((input) => [...input.files]);
  }

  function totalSelected(form) {
    return allPhotoInputs(form).reduce((total, input) => total + input.files.length, 0);
  }

  function updatePreview(zone) {
    if (!zone) return;

    let counter = zone.querySelector('.fh-photo-counter');
    let grid = zone.querySelector('.fh-photo-preview');

    if (!counter) {
      counter = document.createElement('div');
      counter.className = 'fh-photo-counter';
      zone.appendChild(counter);
    }

    if (!grid) {
      grid = document.createElement('div');
      grid.className = 'fh-photo-preview';
      zone.appendChild(grid);
    }

    grid.replaceChildren();

    const files = filesInZone(zone);
    counter.textContent = files.length
      ? `✓ ${files.length}/${MAX_PHOTOS_PER_ZONE} photo${files.length > 1 ? 's' : ''} prête${files.length > 1 ? 's' : ''} à envoyer`
      : 'Aucune photo sélectionnée';

    files.forEach((file) => {
      if (!file.type || !file.type.startsWith('image/')) return;

      const item = document.createElement('div');
      item.className = 'fh-photo-item';

      const img = document.createElement('img');
      img.alt = file.name || 'Photo sélectionnée';
      img.src = URL.createObjectURL(file);
      img.onload = () => URL.revokeObjectURL(img.src);

      const name = document.createElement('span');
      name.className = 'fh-photo-name';
      name.textContent = file.name || 'Photo';

      item.append(img, name);
      grid.appendChild(item);
    });
  }

  function styles() {
    if (document.getElementById('fh-photo-upload-css')) return;

    const style = document.createElement('style');
    style.id = 'fh-photo-upload-css';
    style.textContent = `
      .fh-photo-preview{
        display:grid;
        grid-template-columns:repeat(3,minmax(0,1fr));
        gap:8px;
        margin-top:12px;
      }
      .fh-photo-item{
        position:relative;
        aspect-ratio:1/1;
        overflow:hidden;
        border-radius:12px;
        background:#eef2f6;
        border:1px solid #dce3ea;
      }
      .fh-photo-item img{
        width:100%;
        height:100%;
        object-fit:cover;
        display:block;
      }
      .fh-photo-name{
        position:absolute;
        left:4px;
        right:4px;
        bottom:4px;
        padding:4px 5px;
        border-radius:7px;
        background:rgba(0,0,0,.62);
        color:#fff;
        font-size:10px;
        line-height:1.15;
        overflow:hidden;
        white-space:nowrap;
        text-overflow:ellipsis;
      }
      .fh-photo-counter{
        margin-top:10px;
        color:#18344d;
        font-size:.85rem;
        font-weight:800;
      }
      .fh-photo-input{
        position:absolute!important;
        width:1px!important;
        height:1px!important;
        opacity:0!important;
        pointer-events:none!important;
      }
      .fh-photo-actions{
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:10px;
        margin-top:10px;
      }
      .fh-photo-action{
        border:0;
        border-radius:12px;
        padding:13px 8px;
        background:#edf2f7;
        color:#18344d;
        font-weight:800;
        cursor:pointer;
      }
      .fh-photo-action:active{transform:scale(.98)}
      .fh-photo-upload-status{
        display:none;
        margin-top:12px;
        padding:12px;
        border-radius:12px;
        background:#eaf4ff;
        color:#18344d;
        font-weight:800;
        text-align:center;
      }
      .fh-photo-upload-status.is-visible{display:block}
    `;
    document.head.appendChild(style);
  }

  function makeCameraInput(form, originalInput, zone) {
    const input = document.createElement('input');
    input.type = 'file';
    input.name = originalInput.name;
    input.accept = 'image/*';
    input.capture = 'environment';
    input.multiple = false;
    input.className = 'fh-photo-input';
    input.setAttribute('aria-hidden', 'true');

    input.addEventListener('change', () => {
      if (!input.files.length) return;

      const zoneFiles = filesInZone(zone);
      if (zoneFiles.length > MAX_PHOTOS_PER_ZONE) {
        input.remove();
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);
        return;
      }

      if (totalSelected(form) > MAX_PHOTOS_TOTAL) {
        input.value = '';
        input.remove();
        alert(`Maximum ${MAX_PHOTOS_TOTAL} photos pour ce logement.`);
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

    const picker = document.createElement('button');
    picker.type = 'button';
    picker.className = 'fh-photo-action';
    picker.textContent = '📁 Choisir un fichier';

    camera.addEventListener('click', () => {
      const count = filesInZone(zone).length;
      if (count >= MAX_PHOTOS_PER_ZONE) {
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);
        return;
      }

      if (totalSelected(form) >= MAX_PHOTOS_TOTAL) {
        alert(`Maximum ${MAX_PHOTOS_TOTAL} photos pour ce logement.`);
        return;
      }

      const cameraInput = makeCameraInput(form, input, zone);
      cameraInput.click();
    });

    picker.addEventListener('click', () => {
      const count = filesInZone(zone).length;
      if (count >= MAX_PHOTOS_PER_ZONE) {
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);
        return;
      }

      if (totalSelected(form) >= MAX_PHOTOS_TOTAL) {
        alert(`Maximum ${MAX_PHOTOS_TOTAL} photos pour ce logement.`);
        return;
      }

      input.click();
    });

    actions.append(camera, picker);
    input.parentNode.insertBefore(actions, input);

    const oldLabel = [...zone.querySelectorAll('label')]
      .find((label) => label.htmlFor === input.id);
    if (oldLabel) oldLabel.style.display = 'none';
  }

  function bindInput(form, input) {
    if (input.dataset.fhPhotoBound === '1') return;
    input.dataset.fhPhotoBound = '1';

    input.multiple = true;
    input.accept = 'image/jpeg,image/png,image/webp';
    input.removeAttribute('capture');
    input.classList.add('fh-photo-input');

    addControls(form, input);

    input.addEventListener('change', () => {
      const zone = zoneOf(input);
      let files = [...input.files];

      if (files.length > MAX_PHOTOS_PER_ZONE) {
        /* On ne réécrit pas input.files avec DataTransfer.
         * On laisse le navigateur garder la sélection native.
         * Si le téléphone sélectionne trop de fichiers, on demande de recommencer.
         */
        input.value = '';
        updatePreview(zone);
        alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone. Sélectionnez-en au maximum ${MAX_PHOTOS_PER_ZONE}.`);
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

  function addSubmitStatus(form) {
    if (form.dataset.fhUploadStatusBound === '1') return;
    form.dataset.fhUploadStatusBound = '1';

    const status = document.createElement('div');
    status.className = 'fh-photo-upload-status';
    status.textContent = '⏳ Téléversement des photos en cours… Ne fermez pas cette page.';
    form.appendChild(status);

    form.addEventListener('submit', () => {
      const count = totalSelected(form);
      if (count > 0) {
        status.textContent = `⏳ Téléversement de ${count} photo${count > 1 ? 's' : ''} en cours…`;
        status.classList.add('is-visible');
      }
    });
  }

  function install(form) {
    if (form.dataset.fhNativePhotosInstalled === '1') return;
    form.dataset.fhNativePhotosInstalled = '1';

    styles();
    addSubmitStatus(form);

    const scan = () => {
      allPhotoInputs(form).forEach((input) => bindInput(form, input));
    };

    scan();
    new MutationObserver(scan).observe(form, { childList: true, subtree: true });
  }

  function init() {
    document
      .querySelectorAll('form[enctype="multipart/form-data"]')
      .forEach(install);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
