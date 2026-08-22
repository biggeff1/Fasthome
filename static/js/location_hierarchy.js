(function () {
  'use strict';

  function initLocationHierarchy() {
    const province = document.getElementById('province_select');
    const city = document.getElementById('city_select');
    const subdivision = document.getElementById('subdivision_select');
    if (!province || !city || !subdivision) return;

    const endpoint = '/properties/locations/children/';
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

    async function getChildren(parentId) {
      const url = new URL(endpoint, window.location.origin);
      if (parentId) url.searchParams.set('parent', parentId);
      const response = await fetch(url.toString(), {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const payload = await response.json();
      return payload.results || [];
    }

    async function loadProvinces() {
      resetSelect(province, 'Chargement des provinces…', true);
      resetSelect(city, 'Choisir d’abord une province', true);
      resetSelect(subdivision, 'Choisir d’abord une ville / un territoire', true);
      try {
        const items = await getChildren(null);
        const provinces = items.filter(item => item.kind === 'PROVINCE');
        addOptions(province, provinces);
        province.disabled = false;
        province.options[0].textContent = 'Sélectionner une province';
      } catch (error) {
        resetSelect(province, 'Impossible de charger les provinces', true);
        console.error('Fasthome location hierarchy:', error);
      }
    }

    async function loadCities(provinceId) {
      const serial = ++requestSerial;
      resetSelect(city, 'Chargement des villes / territoires…', true);
      resetSelect(subdivision, 'Choisir d’abord une ville / un territoire', true);
      if (!provinceId) return;
      try {
        const items = await getChildren(provinceId);
        if (serial !== requestSerial) return;
        const cities = items.filter(item => item.kind === 'CITY' || item.kind === 'TERRITORY');
        addOptions(city, cities);
        if (cities.length) {
          city.disabled = false;
          city.options[0].textContent = 'Sélectionner une ville / un territoire';
        } else {
          resetSelect(city, 'Aucune ville / territoire disponible', true);
        }
      } catch (error) {
        if (serial !== requestSerial) return;
        resetSelect(city, 'Erreur de chargement', true);
        console.error('Fasthome location hierarchy:', error);
      }
    }

    async function loadSubdivisions(parentId) {
      const serial = ++requestSerial;
      resetSelect(subdivision, 'Chargement des communes / secteurs / chefferies…', true);
      if (!parentId) return;
      try {
        const items = await getChildren(parentId);
        if (serial !== requestSerial) return;
        const subdivisions = items.filter(item => ['COMMUNE', 'RURAL_COMMUNE', 'SECTOR', 'CHIEFDOM'].includes(item.kind));
        addOptions(subdivision, subdivisions);
        if (subdivisions.length) {
          subdivision.disabled = false;
          subdivision.options[0].textContent = 'Sélectionner une commune / secteur / chefferie';
          subdivision.focus();
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
    loadProvinces();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLocationHierarchy);
  } else {
    initLocationHierarchy();
  }
})();
