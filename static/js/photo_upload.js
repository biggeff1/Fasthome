/* Fasthome — upload photo rapide, aperçu immédiat et envoi multipart fiable. */
(() => {
  'use strict';
  const MAX_PHOTOS_TOTAL = 40;
  const MAX_PHOTOS_PER_ZONE = 5;
  const MAX_DIMENSION = 1280;
  const QUALITY = 0.72;
  const MAX_IMAGE_BYTES = 800_000;
  const CONCURRENCY = 2;

  function photoInputs(form) { return [...form.querySelectorAll('input[type="file"][name^="photos_"]')]; }
  function normalizeInputs(form) {
    photoInputs(form).forEach((input) => {
      input.multiple = true;
      input.accept = 'image/jpeg,image/png,image/webp';
      input.removeAttribute('capture');
    });
  }
  function getZone(input) { return input.closest('[data-photo-zone]') || input.parentElement; }

  function renderPreview(zone, input) {
    let counter = zone.querySelector('.fh-photo-counter');
    let preview = zone.querySelector('.fh-photo-preview');
    if (!counter) { counter = document.createElement('div'); counter.className = 'fh-photo-counter'; zone.appendChild(counter); }
    if (!preview) { preview = document.createElement('div'); preview.className = 'fh-photo-preview'; zone.appendChild(preview); }
    preview.innerHTML = '';
    const files = [...(input.files || [])];
    counter.textContent = files.length ? `${files.length}/${MAX_PHOTOS_PER_ZONE} photo${files.length > 1 ? 's' : ''} sélectionnée${files.length > 1 ? 's' : ''}` : 'Aucune photo sélectionnée';
    files.forEach((file) => {
      if (!file.type.startsWith('image/')) return;
      const item = document.createElement('div'); item.className = 'fh-photo-item';
      const img = document.createElement('img'); img.alt = file.name || 'Photo sélectionnée';
      const url = URL.createObjectURL(file); img.src = url; img.onload = () => URL.revokeObjectURL(url);
      item.appendChild(img); preview.appendChild(item);
    });
  }

  function injectStyles() {
    if (document.getElementById('fh-photo-upload-css')) return;
    const style = document.createElement('style'); style.id = 'fh-photo-upload-css';
    style.textContent = `.fh-photo-preview{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}.fh-photo-item{aspect-ratio:1/1;overflow:hidden;border-radius:10px;background:#eef2f6;border:1px solid #dce3ea}.fh-photo-item img{width:100%;height:100%;object-fit:cover;display:block}.fh-photo-counter{margin-top:8px;color:#64707d;font-size:.82rem;font-weight:700}.fh-photo-input{position:absolute!important;width:1px!important;height:1px!important;opacity:0!important}.fh-photo-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.fh-photo-action{border:0;border-radius:12px;padding:12px 8px;background:#edf2f7;color:#18344d;font-weight:800;cursor:pointer}`;
    document.head.appendChild(style);
  }

  const sleep = () => new Promise((resolve) => setTimeout(resolve, 0));
  function canvasBlob(canvas, quality) {
    return new Promise((resolve, reject) => {
      const done = (blob) => blob ? resolve(blob) : reject(new Error('Impossible d’optimiser une image.'));
      if (typeof canvas.convertToBlob === 'function') canvas.convertToBlob({ type: 'image/webp', quality }).then(done).catch(reject);
      else canvas.toBlob(done, 'image/webp', quality);
    });
  }
  async function loadImage(file) {
    if (typeof createImageBitmap === 'function') { try { return await createImageBitmap(file, { imageOrientation: 'from-image' }); } catch (_) {} }
    const url = URL.createObjectURL(file);
    try { return await new Promise((resolve, reject) => { const img = new Image(); img.onload = () => resolve(img); img.onerror = () => reject(new Error(`Image illisible : ${file.name}`)); img.src = url; }); }
    finally { URL.revokeObjectURL(url); }
  }
  async function compress(file) {
    if (file.size <= MAX_IMAGE_BYTES && file.type === 'image/webp') return file;
    const image = await loadImage(file);
    try {
      const sw = image.naturalWidth || image.width, sh = image.naturalHeight || image.height;
      if (!sw || !sh) throw new Error(`Image illisible : ${file.name}`);
      let scale = Math.min(1, MAX_DIMENSION / Math.max(sw, sh)), quality = QUALITY, blob = null;
      for (let attempt = 0; attempt < 6; attempt += 1) {
        const width = Math.max(1, Math.round(sw * scale)), height = Math.max(1, Math.round(sh * scale));
        const canvas = typeof OffscreenCanvas === 'function' ? new OffscreenCanvas(width, height) : document.createElement('canvas');
        canvas.width = width; canvas.height = height;
        const ctx = canvas.getContext('2d', { alpha: false }); if (!ctx) throw new Error('Canvas indisponible.');
        ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high'; ctx.drawImage(image, 0, 0, width, height);
        blob = await canvasBlob(canvas, quality);
        if (blob.size <= MAX_IMAGE_BYTES) break;
        scale *= Math.max(0.62, Math.min(0.86, Math.sqrt(MAX_IMAGE_BYTES / blob.size) * 0.90)); quality = Math.max(0.50, quality - 0.05); await sleep();
      }
      const stem = file.name.replace(/\.[^.]+$/, '') || 'photo';
      const optimized = new File([blob], `${stem}.webp`, { type: 'image/webp', lastModified: Date.now() });
      return file.size <= MAX_IMAGE_BYTES && file.size <= optimized.size ? file : optimized;
    } finally { if (typeof image.close === 'function') image.close(); }
  }
  function ensureStatus(form) {
    let status = form.querySelector('[data-photo-upload-status]');
    if (!status) { status = document.createElement('div'); status.dataset.photoUploadStatus = 'true'; status.className = 'alert'; status.hidden = true; status.setAttribute('role','status'); const actions = form.querySelector('.actions:last-of-type'); if (actions) actions.before(status); else form.appendChild(status); }
    return status;
  }
  function csrfToken(form) {
    const token = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return token ? token.value : '';
  }
  function uploadFormData(form, formData, status, total) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest(); xhr.open('POST', form.action || window.location.href, true); xhr.withCredentials = true;
      xhr.setRequestHeader('X-Requested-With','XMLHttpRequest');
      const token = csrfToken(form); if (token) xhr.setRequestHeader('X-CSRFToken', token);
      xhr.upload.addEventListener('progress', (event) => { status.textContent = event.lengthComputable ? `Envoi des photos : ${Math.round(event.loaded / event.total * 100)}%` : `Envoi de ${total} photo${total > 1 ? 's' : ''}…`; });
      xhr.addEventListener('load', () => { if (xhr.status >= 200 && xhr.status < 400) resolve(xhr.responseURL || window.location.href); else reject(new Error(`Le serveur a refusé l’envoi des photos (${xhr.status}).`)); });
      xhr.addEventListener('error', () => reject(new Error('Échec de l’envoi des photos. Vérifiez votre connexion puis réessayez.')));
      xhr.addEventListener('abort', () => reject(new Error('Envoi des photos interrompu.')));
      xhr.send(formData);
    });
  }

  async function submitWithOptimizedPhotos(form, submitter) {
    if (form.dataset.photoUploading === '1') return;
    form.dataset.photoUploading = '1';
    const status = ensureStatus(form), inputs = photoInputs(form);
    const filesByInput = inputs.map(input => ({ input, files: [...(input.files || [])] }));
    const total = filesByInput.reduce((sum, item) => sum + item.files.length, 0);
    try {
      if (total > MAX_PHOTOS_TOTAL) throw new Error(`Maximum ${MAX_PHOTOS_TOTAL} photos par logement.`);
      for (const item of filesByInput) if (item.files.length > MAX_PHOTOS_PER_ZONE) throw new Error(`Maximum ${MAX_PHOTOS_PER_ZONE} photos par zone.`);
      status.hidden = false; status.textContent = total ? `Préparation de ${total} photo${total > 1 ? 's' : ''}…` : 'Enregistrement…';
      const formData = new FormData(form, submitter || undefined);
      inputs.forEach(input => formData.delete(input.name));
      const optimizedByInput = new Map();
      const allFiles = filesByInput.flatMap(item => item.files.map(file => ({ input: item.input, file })));
      let completed = 0;
      for (let start = 0; start < allFiles.length; start += CONCURRENCY) {
        const results = await Promise.all(allFiles.slice(start, start + CONCURRENCY).map(async ({ input, file }) => { const optimized = await compress(file); completed += 1; status.textContent = `Optimisation des photos : ${completed}/${total}`; await sleep(); return { input, optimized }; }));
        results.forEach(({ input, optimized }) => { if (!optimizedByInput.has(input.name)) optimizedByInput.set(input.name, []); optimizedByInput.get(input.name).push(optimized); });
      }
      let bytes = 0; optimizedByInput.forEach((files,name) => files.forEach(file => { formData.append(name,file,file.name); bytes += file.size; }));
      status.textContent = total ? `Envoi de ${total} photo${total > 1 ? 's' : ''} (${Math.ceil(bytes / 1000000)} Mo)…` : 'Enregistrement…';
      const responseUrl = await uploadFormData(form, formData, status, total);
      window.location.assign(responseUrl);
    } finally { form.dataset.photoUploading = '0'; }
  }

  function installUpload(form) {
    if (form.dataset.photoUploadInstalled === '1') return;
    form.dataset.photoUploadInstalled = '1'; normalizeInputs(form); injectStyles();
    const observer = new MutationObserver(() => { normalizeInputs(form); bindNewInputs(form); }); observer.observe(form,{childList:true,subtree:true});
    form.addEventListener('submit', async event => {
      if (form.dataset.photoUploading === '1') return;
      event.preventDefault();
      try { await submitWithOptimizedPhotos(form,event.submitter); }
      catch (error) { const status=ensureStatus(form); status.hidden=false; status.textContent=error?.message || 'Impossible de préparer les photos.'; form.dataset.photoUploading='0'; }
    });
    bindNewInputs(form);
  }
  function bindNewInputs(form) {
    photoInputs(form).forEach(input => {
      if (input.dataset.fhPhotoBound === '1') return;
      input.dataset.fhPhotoBound='1'; const zone= getZone(input); if(!zone)return; input.classList.add('fh-photo-input'); input.accept='image/jpeg,image/png,image/webp';
      const oldLabel=[...zone.querySelectorAll('label')].find(label=>label.htmlFor===input.id); if(oldLabel)oldLabel.style.display='none';
      if(!zone.querySelector('.fh-photo-actions')){
        const actions=document.createElement('div'); actions.className='fh-photo-actions';
        const camera=document.createElement('button'); camera.type='button'; camera.className='fh-photo-action'; camera.textContent='📷 Appareil photo'; camera.onclick=()=>{input.setAttribute('capture','environment');input.click();};
        const picker=document.createElement('button'); picker.type='button'; picker.className='fh-photo-action'; picker.textContent='📁 Choisir un fichier'; picker.onclick=()=>{input.removeAttribute('capture');input.click();};
        actions.append(camera,picker); input.parentNode.insertBefore(actions,input);
      }
      input.addEventListener('change',()=>{
        const files=[...(input.files||[])]; if(files.length>MAX_PHOTOS_PER_ZONE){alert(`Maximum ${MAX_PHOTOS_PER_ZONE} photos pour cette zone.`);const dt=new DataTransfer();files.slice(0,MAX_PHOTOS_PER_ZONE).forEach(f=>dt.items.add(f));input.files=dt.files;}
        renderPreview(zone,input);
      });
      renderPreview(zone,input);
    });
  }
  function init(){document.querySelectorAll('form[enctype="multipart/form-data"]').forEach(installUpload);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
