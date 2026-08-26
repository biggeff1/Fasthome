/* Fasthome — appareil photo natif pour les photos de logement. */
(() => {
  'use strict';
  const MAX_PER_ZONE = 5;
  const INPUT_SELECTOR = 'input[type="file"][name^="photos_"]';

  function addFilesToInput(target, files) {
    const current = [...(target.files || [])];
    const incoming = [...files];
    if (current.length + incoming.length > MAX_PER_ZONE) {
      alert(`Maximum ${MAX_PER_ZONE} photos pour cette zone.`);
      return;
    }
    const dt = new DataTransfer();
    [...current, ...incoming].forEach(file => dt.items.add(file));
    target.files = dt.files;
    target.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function refreshCameraButtons() {
    document.querySelectorAll(INPUT_SELECTOR).forEach(input => {
      if (input.dataset.nativeCameraReady === '1') return;
      input.dataset.nativeCameraReady = '1';

      const wrapper = input.closest('.photo-slot') || input.parentElement;
      if (!wrapper || wrapper.querySelector('[data-native-camera-button]')) return;

      const cameraInput = document.createElement('input');
      cameraInput.type = 'file';
      cameraInput.accept = 'image/*';
      cameraInput.setAttribute('capture', 'environment');
      cameraInput.multiple = false;
      cameraInput.hidden = true;
      cameraInput.setAttribute('aria-hidden', 'true');

      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.nativeCameraButton = '1';
      button.className = 'btn btn-light native-camera-button';
      button.textContent = '📷 Prendre une photo';
      button.addEventListener('click', () => cameraInput.click());

      input.insertAdjacentElement('afterend', button);
      input.insertAdjacentElement('afterend', cameraInput);
      cameraInput.addEventListener('change', () => {
        if (cameraInput.files?.length) addFilesToInput(input, cameraInput.files);
        cameraInput.value = '';
      });
    });
  }

  function init() {
    const observer = new MutationObserver(refreshCameraButtons);
    observer.observe(document.body, { childList: true, subtree: true });
    refreshCameraButtons();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
