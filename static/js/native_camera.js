/* Fasthome — sélection photo native : appareil photo ou fichier. */
(() => {
  'use strict';

  const MAX_PER_ZONE = 5;
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';

  function addFilesToInput(target, files) {
    const current = [...(target.files || [])];
    const incoming = [...files];
    if (!incoming.length) return;

    const remaining = MAX_PER_ZONE - current.length;
    if (remaining <= 0) {
      alert(`Maximum ${MAX_PER_ZONE} photos pour cette zone.`);
      return;
    }

    const accepted = incoming.slice(0, remaining);
    if (accepted.length < incoming.length) {
      alert(`Maximum ${MAX_PER_ZONE} photos pour cette zone.`);
    }

    const dt = new DataTransfer();
    [...current, ...accepted].forEach((file) => dt.items.add(file));
    target.files = dt.files;
    target.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function makeButton(text, className) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `btn btn-light native-photo-button ${className}`;
    button.textContent = text;
    return button;
  }

  function refreshPhotoControls() {
    document.querySelectorAll(INPUT_SELECTOR).forEach((input) => {
      if (input.dataset.nativePhotoReady === '1') return;

      const wrapper = input.closest('.photo-slot') || input.parentElement;
      if (!wrapper) return;
      if (wrapper.querySelector('[data-native-photo-controls]')) {
        input.dataset.nativePhotoReady = '1';
        return;
      }

      input.dataset.nativePhotoReady = '1';
      input.multiple = true;
      input.accept = 'image/jpeg,image/png,image/webp';
      input.hidden = true;
      input.setAttribute('aria-hidden', 'true');

      // Champ séparé uniquement pour ouvrir l'appareil photo natif.
      // Il ne porte pas de name : la photo est ensuite ajoutée au champ principal.
      const cameraInput = document.createElement('input');
      cameraInput.type = 'file';
      cameraInput.accept = 'image/*';
      cameraInput.setAttribute('capture', 'environment');
      cameraInput.multiple = false;
      cameraInput.hidden = true;
      cameraInput.setAttribute('aria-hidden', 'true');

      const controls = document.createElement('div');
      controls.dataset.nativePhotoControls = '1';
      controls.className = 'native-photo-controls';

      const cameraButton = makeButton('📷 Appareil photo', 'native-camera-button');
      const fileButton = makeButton('📁 Choisir un fichier', 'native-file-button');

      cameraButton.addEventListener('click', () => cameraInput.click());
      fileButton.addEventListener('click', () => input.click());

      cameraInput.addEventListener('change', () => {
        addFilesToInput(input, cameraInput.files || []);
        cameraInput.value = '';
      });

      controls.append(cameraButton, fileButton);
      input.insertAdjacentElement('afterend', cameraInput);
      input.insertAdjacentElement('afterend', controls);
    });
  }

  function init() {
    refreshPhotoControls();
    const observer = new MutationObserver(refreshPhotoControls);
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
