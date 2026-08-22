(function () {
  'use strict';

  function initLocationHierarchy() {
    const province = document.getElementById('province_select');
    const city = document.getElementById('city_select');
    const subdivision = document.getElementById('subdivision_select');
    if (!province || !city || !subdivision) return;

    const endpoint = '/properties/locations/children/';
    const subdivisionKinds = ['COMMUNE', 'RURAL_COMMUNE', 'SECTOR', 'CHIEFDOM'];
    let requestSerial = 0;

    function resetSelect(select, placeholder, disabled) {
      select.innerHTML = '';
      const option = document.createElement('option');
      option.value = '';
      option.textContent = placeholder;
      select.appendChild(option);
      select.disabled = disabled;
    }

    function addOptions(select, items) {
      items.forEach(function (item) {
        const option = document.createElement('option');
        option.value = String(item.id);
        option.textContent = item.name;
        option.dataset.kind = item.kind || '';
        select.appendChild(option);
      });
    }

    async function getChildren(parentId, kinds) {
      const responses = await Promise.all(kinds.map(async function (kind) {
        const url = new URL(endpoint, window.location.origin);
        if (parentId) url.searchParams.set('parent', parentId);
        url.searchParams.set('kind', kind);
        const response = await fetch(url.toString(), {
          method: 'GET',
          credentials: 'same-origin',
          headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const payload = await response.json();
        return payload.results || [];
      }));
      const merged = [];
      const seen = new Set();
      responses.flat().forEach(function (item) {
        if (!seen.has(item.id)) {
          seen.add(item.id);
          merged.push(item);
        }
      });
      merged.sort(function (a, b) { return a.name.localeCompare(b.name, 'fr'); });
      return merged;
    }

    async function loadProvinces() {
      resetSelect(province, 'Chargement des provinces…', true);
      resetSelect(city, 'Choisir d’abord une province', true);
      resetSelect(subdivision, 'Choisir d’abord une ville / un territoire', true);
      try {
        const items = await getChildren(null, ['PROVINCE']);
        addOptions(province, items);
        province.disabled = false;
        province.options[0].textContent = 'Sélectionner une province';
      } catch (error) {
        resetSelect(province, 'Impossible de charger les provinces', true);
        resetSelect(city, 'Province indisponible', true);
        resetSelect(subdivision, 'Subdivision indisponible', true);
        console.error('Fasthome location hierarchy:', error);
      }
    }

    async function loadCities(provinceId) {
      const serial = ++requestSerial;
      resetSelect(city, 'Chargement des villes / territoires…', true);
      resetSelect(subdivision, 'Choisir d’abord une ville / un territoire', true);
      if (!provinceId) {
        resetSelect(city, 'Choisir d’abord une province', true);
        return;
      }
      try {
        const items = await getChildren(provinceId, ['CITY', 'TERRITORY']);
        if (serial !== requestSerial) return;
        addOptions(city, items);
        if (items.length) {
          city.disabled = false;
          city.options[0].textContent = 'Sélectionner une ville / un territoire';
        } else {
          resetSelect(city, 'Aucune ville / territoire disponible', true);
        }
      } catch (error) {
        if (serial !== requestSerial) return;
        resetSelect(city, 'Erreur de chargement', true);
        resetSelect(subdivision, 'Subdivision indisponible', true);
        console.error('Fasthome location hierarchy:', error);
      }
    }

    async function loadSubdivisions(parentId) {
      const serial = ++requestSerial;
      resetSelect(subdivision, 'Chargement des subdivisions…', true);
      if (!parentId) {
        resetSelect(subdivision, 'Choisir d’abord une ville / un territoire', true);
        return;
      }
      try {
        const items = await getChildren(parentId, subdivisionKinds);
        if (serial !== requestSerial) return;
        addOptions(subdivision, items);
        if (items.length) {
          subdivision.disabled = false;
          subdivision.options[0].textContent = 'Sélectionner une commune / secteur / chefferie';
        } else {
          resetSelect(subdivision, 'Aucune subdivision disponible pour ce parent', true);
        }
      } catch (error) {
        if (serial !== requestSerial) return;
        resetSelect(subdivision, 'Erreur de chargement des subdivisions', true);
        console.error('Fasthome location hierarchy:', error);
      }
    }

    province.addEventListener('change', function () { loadCities(this.value); });
    city.addEventListener('change', function () { loadSubdivisions(this.value); });

    // The creation flow starts with no selection. The backend still enforces
    // the parent-child relationship when the form is submitted.
    loadProvinces();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLocationHierarchy);
  } else {
    initLocationHierarchy();
  }
})();
