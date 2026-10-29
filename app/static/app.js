/**
 * FERROSTATS — MANAGERIAL PORTAL (WAREHOUSE AUDITING & GOOGLE LOOKER BI)
 * Author & Lead Architect: Diego Alejandro Escobar Barahona
 * Tech Stack: Vanilla JS + Lucide Icons + Google BigQuery Medallion Architecture
 */

const DEFAULT_LOOKER_URL = 'https://datastudio.google.com/embed/reporting/2389e684-fc9b-431d-9c56-487b3067eb87/page/p_dwbfqrtk8d';

const AppTranslations = {
  en: {
    langLabel: 'EN',
    statusOptimal: 'Optimal',
    statusLowStock: 'Low Stock',
    statusOutOfStock: 'Out of Stock',
    unitLabel: 'Unit:',
    classLabel: 'Class',
    currentStockLabel: 'Current Stock',
    minStockLabel: 'Minimum',
    burnRateLabel: 'Burn Rate',
    restockBtn: 'Supplier Restock / Audit',
    orderBtn: 'Order',
    itemsAtRisk: 'items at risk',
    inventoryHealthy: 'All inventory levels are currently above reorder thresholds.',
    noItemsInAisle: 'No products found in this aisle matching selected filters.',
    stockNegativeErr: 'Operation canceled: stock cannot be negative.',
    stockUpdatedToast: 'Stock updated: ',
    adjustAppliedToast: 'Adjustment applied: new stock ',
    syncRefreshingToast: 'Refreshing Dataform models & syncing BigQuery...',
    syncSuccessToast: 'Looker Studio dashboard refreshed successfully.',
    urlResetToast: 'Looker URL reset to default.',
    validQuantityErr: 'Please enter a valid non-zero quantity.'
  },
  es: {
    langLabel: 'ES',
    statusOptimal: 'Óptimo',
    statusLowStock: 'Bajo Stock',
    statusOutOfStock: 'Agotado',
    unitLabel: 'Unidad:',
    classLabel: 'Clase',
    currentStockLabel: 'Stock Actual',
    minStockLabel: 'Mínimo',
    burnRateLabel: 'Burn Rate',
    restockBtn: 'Ingreso de Proveedor / Conteo',
    orderBtn: 'Pedir',
    itemsAtRisk: 'artículos en riesgo',
    inventoryHealthy: '¡Excelente! Todo el inventario se encuentra por encima del stock de reorden.',
    noItemsInAisle: 'No hay artículos en este pasillo con el filtro seleccionado.',
    stockNegativeErr: 'Operación cancelada: el stock no puede ser negativo.',
    stockUpdatedToast: 'Stock actualizado: ',
    adjustAppliedToast: 'Ajuste aplicado: nuevo stock ',
    syncRefreshingToast: 'Actualizando transformaciones y sincronizando datos...',
    syncSuccessToast: 'Dashboard de Looker Studio recargado.',
    urlResetToast: 'URL restablecida a la predeterminada.',
    validQuantityErr: 'Ingresa una cantidad válida distinta de 0.'
  }
};

const State = {
  lang: localStorage.getItem('ferrostats_lang') || 'en',
  activeTab: 'bodega', // 'bodega', 'bi'
  products: [],
  selectedAisle: 'TODOS',
  onlyCriticalAisles: false,
  analyticsData: null,
  lookerUrl: localStorage.getItem('ferrostats_looker_url') || DEFAULT_LOOKER_URL
};

function t(key) {
  const dict = AppTranslations[State.lang] || AppTranslations.en;
  return dict[key] || AppTranslations.en[key] || key;
}

document.addEventListener('DOMContentLoaded', () => {
  initLanguageToggle();
  initBottomNav();
  initLookerControls();
  initLookerConfigModal();
  initWarehouseControls();
  loadWarehouseData();
  updateLookerDisplay();
  refreshIcons();
});

function refreshIcons() {
  if (window.lucide) {
    window.lucide.createIcons({
      attrs: { 'stroke-width': 1.75 }
    });
  }
}

function initLanguageToggle() {
  const btn = document.getElementById('btnMainLangToggle');
  const label = document.getElementById('mainLangLabel');
  if (label) label.textContent = State.lang.toUpperCase();

  btn?.addEventListener('click', () => {
    State.lang = State.lang === 'en' ? 'es' : 'en';
    localStorage.setItem('ferrostats_lang', State.lang);
    if (label) label.textContent = State.lang.toUpperCase();
    renderWarehouseCards();
    if (State.analyticsData) {
      renderReorderTable(State.analyticsData.reorder_priority_list || []);
    }
  });
}

async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Role': 'ADMIN',
    'X-User-Id': '1',
    ...(options.headers || {})
  };

  const res = await fetch(endpoint, { ...options, headers });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `HTTP Error ${res.status}`);
  }
  return data;
}

// ==============================================================================
// 1. BOTTOM NAVIGATION (WAREHOUSE | LOOKER BI)
// ==============================================================================
function initBottomNav() {
  const navItems = document.querySelectorAll('.bottom-nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });
}

function switchTab(tab) {
  State.activeTab = tab;

  document.querySelectorAll('.bottom-nav-item').forEach(item => {
    const isTarget = item.getAttribute('data-tab') === tab;
    item.classList.toggle('active', isTarget);
  });

  document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));

  if (tab === 'bodega') {
    document.getElementById('viewBodega')?.classList.add('active');
    loadWarehouseData();
  } else if (tab === 'bi') {
    document.getElementById('viewBi')?.classList.add('active');
    updateLookerDisplay();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
  refreshIcons();
}

// ==============================================================================
// 2. WAREHOUSE CONTROLS & PHYSICAL AUDITING
// ==============================================================================
function initWarehouseControls() {
  document.querySelectorAll('#aisleTabs .aisle-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#aisleTabs .aisle-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      State.selectedAisle = btn.getAttribute('data-aisle') || 'TODOS';
      renderWarehouseCards();
    });
  });

  document.getElementById('chkOnlyCriticalAisles')?.addEventListener('change', (e) => {
    State.onlyCriticalAisles = e.target.checked;
    renderWarehouseCards();
  });

  document.getElementById('btnCloseAdjustModal')?.addEventListener('click', closeAdjustModal);
  document.getElementById('btnCancelAdjust')?.addEventListener('click', closeAdjustModal);
  document.getElementById('btnSaveAdjust')?.addEventListener('click', saveAdjustMovement);
}

async function loadWarehouseData() {
  try {
    const [products, analytics] = await Promise.all([
      apiFetch('/api/v1/products'),
      apiFetch('/api/v1/analytics/dashboard')
    ]);
    State.products = products;
    State.analyticsData = analytics;

    renderWarehouseCards();
    renderReorderTable(analytics.reorder_priority_list || []);
  } catch (err) {
    showToast(`Failed to load warehouse data: ${err.message}`, 'error');
  }
}

function renderWarehouseCards() {
  const grid = document.getElementById('warehouseCardsGrid');
  if (!grid) return;
  grid.innerHTML = '';

  let filtered = State.products;

  if (State.selectedAisle !== 'TODOS') {
    filtered = filtered.filter(p => p.aisle_location.startsWith(State.selectedAisle));
  }

  if (State.onlyCriticalAisles) {
    filtered = filtered.filter(p => p.stock_status === 'AGOTADO' || p.stock_status === 'BAJO_STOCK');
  }

  if (filtered.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: #94a3b8;">${t('noItemsInAisle')}</div>`;
    refreshIcons();
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement('div');
    card.className = 'wh-card';

    let statusText = t('statusOptimal');
    let statusClass = 'wh-status-optimo';
    let statusIcon = 'check-circle-2';

    if (p.stock_status === 'AGOTADO') {
      statusText = t('statusOutOfStock');
      statusClass = 'wh-status-agotado';
      statusIcon = 'alert-circle';
    } else if (p.stock_status === 'BAJO_STOCK') {
      statusText = t('statusLowStock');
      statusClass = 'wh-status-reorden';
      statusIcon = 'alert-triangle';
    }

    card.innerHTML = `
      <div>
        <div class="wh-card-top">
          <div class="wh-card-meta">
            <span class="wh-sku-clean">${p.sku}</span>
            <span class="wh-meta-sep">•</span>
            <span class="wh-location-clean"><i data-lucide="map-pin"></i> ${p.aisle_location}</span>
          </div>
          <div class="wh-status-clean ${statusClass}">
            <i data-lucide="${statusIcon}"></i>
            <span>${statusText}</span>
          </div>
        </div>
        <div class="wh-prod-name">${escapeHtml(p.product_name)}</div>
        <div class="wh-prod-measure">${t('unitLabel')} ${p.unit_measure} • ${t('classLabel')} ${p.abc_class || 'A'}</div>
        
        <div class="wh-stock-section">
          <div class="wh-stock-col wh-stock-primary">
            <span class="wh-metric-label">${t('currentStockLabel')}</span>
            <div class="wh-metric-val-lg" id="whStockVal-${p.product_id}">${p.current_stock}</div>
          </div>
          <div class="wh-stock-divider"></div>
          <div class="wh-stock-col">
            <span class="wh-metric-label">${t('minStockLabel')}</span>
            <div class="wh-metric-val">${p.min_stock}</div>
          </div>
          <div class="wh-stock-divider"></div>
          <div class="wh-stock-col">
            <span class="wh-metric-label">${t('burnRateLabel')}</span>
            <div class="wh-metric-val">${p.daily_burn_rate || 0}<small>/d</small></div>
          </div>
        </div>
      </div>

      <div>
        <div class="wh-touch-actions">
          <button class="btn-touch" onclick="quickAdjust(${p.product_id}, -1)">-1</button>
          <button class="btn-touch" onclick="quickAdjust(${p.product_id}, 1)">+1</button>
          <button class="btn-touch" onclick="quickAdjust(${p.product_id}, 5)">+5</button>
          <button class="btn-touch" onclick="quickAdjust(${p.product_id}, 10)">+10</button>
        </div>
        <button class="btn-touch-modal" onclick="openAdjustModal(${p.product_id}, '${p.sku}', '${escapeHtml(p.product_name)}', ${p.current_stock}, 15)">
          <i data-lucide="truck"></i> ${t('restockBtn')}
        </button>
      </div>
    `;
    grid.appendChild(card);
  });

  refreshIcons();
}

async function quickAdjust(productId, delta) {
  const prod = State.products.find(p => p.product_id === productId);
  if (!prod) return;

  if (prod.current_stock + delta < 0) {
    showToast(t('stockNegativeErr'), 'error');
    return;
  }

  const movType = delta > 0 ? 'INGRESO_PROVEEDOR' : 'AJUSTE_AUDITORIA';
  const payload = {
    product_id: productId,
    user_id: 1,
    movement_type: movType,
    quantity_delta: delta,
    reference_note: `Quick touch adjustment (${delta > 0 ? '+' : ''}${delta}) at aisle ${prod.aisle_location}`
  };

  try {
    const res = await apiFetch('/api/v1/inventory/adjust', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    prod.current_stock = res.stock_after;
    if (prod.current_stock === 0) {
      prod.stock_status = 'AGOTADO';
    } else if (prod.current_stock <= prod.min_stock) {
      prod.stock_status = 'BAJO_STOCK';
    } else {
      prod.stock_status = 'OPTIMO';
    }

    renderWarehouseCards();
    showToast(`${t('stockUpdatedToast')}${prod.sku} = ${res.stock_after} units`, 'success');
  } catch (err) {
    showToast(`Error adjusting stock: ${err.message}`, 'error');
  }
}

function openAdjustModal(productId, sku, name, currentStock, suggestedDelta) {
  document.getElementById('adjustProductId').value = productId;
  document.getElementById('adjustModalSku').textContent = sku;
  document.getElementById('adjustModalName').textContent = name;
  document.getElementById('adjustModalCurrentStock').textContent = currentStock;
  document.getElementById('adjustQuantityDelta').value = suggestedDelta || 10;
  document.getElementById('adjustNote').value = `Supplier Restock Aisle`;
  document.getElementById('modalAdjustOverlay')?.classList.add('active');
}

function closeAdjustModal() {
  document.getElementById('modalAdjustOverlay')?.classList.remove('active');
}

async function saveAdjustMovement() {
  const productId = parseInt(document.getElementById('adjustProductId').value, 10);
  const movType = document.getElementById('adjustMovementType').value;
  const delta = parseInt(document.getElementById('adjustQuantityDelta').value, 10);
  const note = document.getElementById('adjustNote').value.trim();

  if (isNaN(delta) || delta === 0) {
    showToast(t('validQuantityErr'), 'error');
    return;
  }

  const payload = {
    product_id: productId,
    user_id: 1,
    movement_type: movType,
    quantity_delta: delta,
    reference_note: note || 'Manual warehouse adjustment'
  };

  try {
    const res = await apiFetch('/api/v1/inventory/adjust', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    closeAdjustModal();
    showToast(`${t('adjustAppliedToast')}${res.stock_after} units`, 'success');
    loadWarehouseData();
  } catch (err) {
    showToast(`Failed to save adjustment: ${err.message}`, 'error');
  }
}

function renderReorderTable(items) {
  const tbody = document.querySelector('#tableReorder tbody') || document.querySelector('#tableReorder');
  const countBadge = document.getElementById('reorderCountBadge');
  if (!tbody) return;

  if (countBadge) {
    countBadge.textContent = `${items.length} ${t('itemsAtRisk')}`;
  }

  let targetTbody = tbody.tagName === 'TBODY' ? tbody : tbody.querySelector('tbody');
  if (!targetTbody) {
    targetTbody = document.createElement('tbody');
    tbody.appendChild(targetTbody);
  }
  targetTbody.innerHTML = '';

  if (items.length === 0) {
    targetTbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: #10b981; padding: 2rem;">${t('inventoryHealthy')}</td></tr>`;
    return;
  }

  items.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td data-label="SKU"><code>${p.sku}</code></td>
      <td data-label="Product Name"><strong>${escapeHtml(p.product_name)}</strong></td>
      <td data-label="Category">${p.category_name}</td>
      <td data-label="Location"><i data-lucide="map-pin"></i> ${p.aisle_location || 'Aisle A'}</td>
      <td data-label="ABC Class"><span class="badge-abc-${(p.abc_class || 'A').toLowerCase()}">${p.abc_class || 'A'}</span></td>
      <td data-label="Stock / Min"><strong>${p.current_stock}</strong> <small>(min ${p.min_stock})</small></td>
      <td data-label="Burn Rate">${p.daily_burn_rate}</td>
      <td data-label="DOI (Days)"><strong>${p.days_of_inventory_left} d</strong></td>
      <td data-label="Suggested Reorder"><strong class="text-accent">+${p.recommended_reorder_qty}</strong></td>
      <td data-label="Supplier"><small>${p.supplier_name}<br>${p.contact_phone}</small></td>
      <td data-label="Action">
        <button class="btn btn-secondary btn-sm" onclick="openAdjustModal(${p.product_id}, '${p.sku}', '${escapeHtml(p.product_name)}', ${p.current_stock}, ${p.recommended_reorder_qty})">
          <i data-lucide="truck"></i> ${t('orderBtn')}
        </button>
      </td>
    `;
    targetTbody.appendChild(tr);
  });

  refreshIcons();
}

// ==============================================================================
// 3. LOOKER STUDIO EMBED & DATAFORM SYNC
// ==============================================================================
function initLookerControls() {
  document.getElementById('btnReloadLooker')?.addEventListener('click', async () => {
    const btn = document.getElementById('btnReloadLooker');
    const iframe = document.getElementById('lookerIframe');

    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i data-lucide="loader-2" class="spin"></i> <span>Syncing...</span>';
      refreshIcons();
    }

    showToast(t('syncRefreshingToast'), 'info');

    try {
      const res = await apiFetch('/api/v1/etl/run', { method: 'POST' });
      showToast(res.message || t('syncSuccessToast'), 'success');
    } catch (err) {
      console.warn('Note on ETL refresh:', err);
      showToast('Reloading report view...', 'info');
    } finally {
      if (iframe && State.lookerUrl) {
        const cleanUrl = State.lookerUrl;
        iframe.src = 'about:blank';
        setTimeout(() => {
          iframe.src = cleanUrl;
        }, 120);
      }
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHtml || '<i data-lucide="rotate-cw"></i> <span>Refresh Dataform &amp; Sync</span>';
        refreshIcons();
      }
    }
  });

  document.getElementById('btnOpenConfigModalFromFallback')?.addEventListener('click', () => {
    document.getElementById('btnConfigureLookerUrl')?.click();
  });
}

function updateLookerDisplay() {
  const iframe = document.getElementById('lookerIframe');
  const fallback = document.getElementById('lookerOfflineFallback');
  const linkFull = document.getElementById('linkOpenLookerFull');

  if (State.lookerUrl && State.lookerUrl.trim().length > 0) {
    if (iframe) {
      iframe.src = State.lookerUrl;
      iframe.style.display = 'block';
    }
    if (linkFull) {
      linkFull.href = State.lookerUrl.replace('/embed', '');
    }
    if (fallback) fallback.classList.remove('active');
  } else {
    if (iframe) {
      iframe.src = 'about:blank';
      iframe.style.display = 'none';
    }
    if (fallback) fallback.classList.add('active');
  }
}

function initLookerConfigModal() {
  const modal = document.getElementById('modalLookerConfigOverlay');
  const inputUrl = document.getElementById('inputLookerUrl');

  document.getElementById('btnConfigureLookerUrl')?.addEventListener('click', () => {
    inputUrl.value = State.lookerUrl;
    modal?.classList.add('active');
  });

  document.getElementById('btnResetDefaultLookerUrl')?.addEventListener('click', () => {
    inputUrl.value = DEFAULT_LOOKER_URL;
    showToast(t('urlResetToast'), 'info');
  });

  document.getElementById('btnCloseLookerConfigModal')?.addEventListener('click', () => {
    modal?.classList.remove('active');
  });

  document.getElementById('btnCancelLookerConfig')?.addEventListener('click', () => {
    modal?.classList.remove('active');
  });

  document.getElementById('btnSaveLookerConfig')?.addEventListener('click', () => {
    const newUrl = inputUrl.value.trim() || DEFAULT_LOOKER_URL;
    State.lookerUrl = newUrl;
    localStorage.setItem('ferrostats_looker_url', newUrl);
    updateLookerDisplay();
    modal?.classList.remove('active');
    showToast('Looker Studio URL updated successfully.', 'success');
  });
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let iconName = 'info';
  if (type === 'success') iconName = 'check-circle';
  if (type === 'error') iconName = 'alert-triangle';

  toast.innerHTML = `<i data-lucide="${iconName}"></i> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  refreshIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.25s ease-out';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[m]);
}
