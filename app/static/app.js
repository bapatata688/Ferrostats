/**
 * FERROSTATS — PORTAL GERENCIAL (BODEGA, LOOKER STUDIO & DATAFORM OBSERVABILITY)
 * Author: Diego Alejandro Escobar Barahona
 * Framework: Vanilla JS + Lucide Icons + BigQuery / Dataform Medallion Architecture
 */

const DEFAULT_LOOKER_URL = 'https://datastudio.google.com/embed/reporting/2389e684-fc9b-431d-9c56-487b3067eb87/page/p_dwbfqrtk8d';

const State = {
  activeTab: 'bodega', // 'bodega', 'bi', 'dataform'
  products: [],
  selectedAisle: 'TODOS',
  onlyCriticalAisles: false,
  analyticsData: null,
  dataformStats: null,
  lookerUrl: localStorage.getItem('ferrostats_looker_url') || DEFAULT_LOOKER_URL
};

document.addEventListener('DOMContentLoaded', () => {
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
    throw new Error(data.detail || `Error HTTP ${res.status}`);
  }
  return data;
}

// ==============================================================================
// 1. NAVEGACIÓN INFERIOR (FOOTER NAV: BODEGA | LOOKER BI | DATAFORM ELT)
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

  // Actualizar items de la barra inferior
  document.querySelectorAll('.bottom-nav-item').forEach(item => {
    const isTarget = item.getAttribute('data-tab') === tab;
    item.classList.toggle('active', isTarget);
  });

  // Conmutar secciones
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
// 2. SECCIÓN BODEGA: CONTROL FÍSICO Y AUDITORÍA EN PASILLOS
// ==============================================================================
function initWarehouseControls() {
  // Tabs de pasillos
  document.querySelectorAll('#aisleTabs .aisle-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#aisleTabs .aisle-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      State.selectedAisle = btn.getAttribute('data-aisle') || 'TODOS';
      renderWarehouseCards();
    });
  });

  // Filtro de críticos
  document.getElementById('chkOnlyCriticalAisles')?.addEventListener('change', (e) => {
    State.onlyCriticalAisles = e.target.checked;
    renderWarehouseCards();
  });

  // Modal ajuste inventario
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
    showToast(`Error al cargar bodega: ${err.message}`, 'error');
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
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: #94a3b8;">No hay artículos en este pasillo con el filtro seleccionado.</div>';
    refreshIcons();
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement('div');
    card.className = 'wh-card';

    let statusText = 'Óptimo';
    let statusClass = 'wh-status-optimo';
    let statusIcon = 'check-circle-2';

    if (p.stock_status === 'AGOTADO') {
      statusText = 'Agotado';
      statusClass = 'wh-status-agotado';
      statusIcon = 'alert-circle';
    } else if (p.stock_status === 'BAJO_STOCK') {
      statusText = 'Bajo Stock';
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
        <div class="wh-prod-measure">Unidad: ${p.unit_measure} • Clase ${p.abc_class || 'A'}</div>
        
        <div class="wh-stock-section">
          <div class="wh-stock-col wh-stock-primary">
            <span class="wh-metric-label">Stock Actual</span>
            <div class="wh-metric-val-lg" id="whStockVal-${p.product_id}">${p.current_stock}</div>
          </div>
          <div class="wh-stock-divider"></div>
          <div class="wh-stock-col">
            <span class="wh-metric-label">Mínimo</span>
            <div class="wh-metric-val">${p.min_stock}</div>
          </div>
          <div class="wh-stock-divider"></div>
          <div class="wh-stock-col">
            <span class="wh-metric-label">Burn Rate</span>
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
          <i data-lucide="truck"></i> Ingreso de Proveedor / Conteo
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
    showToast(`Operación cancelada: el stock no puede ser negativo.`, 'error');
    return;
  }

  const movType = delta > 0 ? 'INGRESO_PROVEEDOR' : 'AJUSTE_AUDITORIA';
  const payload = {
    product_id: productId,
    user_id: 1,
    movement_type: movType,
    quantity_delta: delta,
    reference_note: `Ajuste táctil rápido (${delta > 0 ? '+' : ''}${delta}) en pasillo ${prod.aisle_location}`
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
    showToast(`Stock actualizado: ${prod.sku} = ${res.stock_after} uds`, 'success');
  } catch (err) {
    showToast(`Error al ajustar: ${err.message}`, 'error');
  }
}

function openAdjustModal(productId, sku, name, currentStock, suggestedDelta) {
  document.getElementById('adjustProductId').value = productId;
  document.getElementById('adjustModalSku').textContent = sku;
  document.getElementById('adjustModalName').textContent = name;
  document.getElementById('adjustModalCurrentStock').textContent = currentStock;
  document.getElementById('adjustQuantityDelta').value = suggestedDelta || 10;
  document.getElementById('adjustNote').value = `Ingreso factura pasillo`;
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
    showToast('Ingresa una cantidad válida distinta de 0', 'error');
    return;
  }

  const payload = {
    product_id: productId,
    user_id: 1,
    movement_type: movType,
    quantity_delta: delta,
    reference_note: note || 'Ajuste de bodega manual'
  };

  try {
    const res = await apiFetch('/api/v1/inventory/adjust', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    closeAdjustModal();
    showToast(`Ajuste aplicado: nuevo stock ${res.stock_after} uds`, 'success');
    loadWarehouseData();
  } catch (err) {
    showToast(`Error al guardar ajuste: ${err.message}`, 'error');
  }
}

function renderReorderTable(items) {
  const tbody = document.querySelector('#tableReorder tbody') || document.querySelector('#tableReorder');
  const countBadge = document.getElementById('reorderCountBadge');
  if (!tbody) return;

  if (countBadge) {
    countBadge.textContent = `${items.length} artículos en riesgo`;
  }

  // Si tableReorder no tiene tbody explícito
  let targetTbody = tbody.tagName === 'TBODY' ? tbody : tbody.querySelector('tbody');
  if (!targetTbody) {
    targetTbody = document.createElement('tbody');
    tbody.appendChild(targetTbody);
  }
  targetTbody.innerHTML = '';

  if (items.length === 0) {
    targetTbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #10b981; padding: 2rem;">¡Excelente! Todo el inventario se encuentra por encima del stock de reorden.</td></tr>';
    return;
  }

  items.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td data-label="SKU"><code>${p.sku}</code></td>
      <td data-label="Artículo"><strong>${escapeHtml(p.product_name)}</strong></td>
      <td data-label="Familia">${p.category_name}</td>
      <td data-label="Stock Actual"><strong>${p.current_stock}</strong> <small>(mín ${p.min_stock})</small></td>
      <td data-label="Burn Rate">${p.daily_burn_rate}</td>
      <td data-label="Días DOI"><strong>${p.days_of_inventory_left} d</strong></td>
      <td data-label="Sugerido"><strong class="text-accent">+${p.recommended_reorder_qty}</strong></td>
      <td data-label="Proveedor"><small>${p.supplier_name}<br>${p.contact_phone}</small></td>
      <td data-label="Acción">
        <button class="btn btn-secondary btn-sm" onclick="openAdjustModal(${p.product_id}, '${p.sku}', '${escapeHtml(p.product_name)}', ${p.current_stock}, ${p.recommended_reorder_qty})">
          <i data-lucide="truck"></i> Pedir
        </button>
      </td>
    `;
    targetTbody.appendChild(tr);
  });

  refreshIcons();
}

// ==============================================================================
// 3. SECCIÓN BI EXCLUSIVO: GOOGLE LOOKER STUDIO
// ==============================================================================
function initLookerControls() {
  document.getElementById('btnReloadLooker')?.addEventListener('click', async () => {
    const btn = document.getElementById('btnReloadLooker');
    const iframe = document.getElementById('lookerIframe');

    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i data-lucide="loader-2" class="spin"></i> <span>Actualizando...</span>';
      refreshIcons();
    }

    showToast('Actualizando transformaciones y sincronizando datos...', 'info');

    try {
      // 1. Ejecutar las transformaciones y sincronización en backend hacia BigQuery
      const res = await apiFetch('/api/v1/etl/run', { method: 'POST' });
      showToast(res.message || 'Transformaciones actualizadas exitosamente', 'success');
    } catch (err) {
      console.warn('Nota en actualización:', err);
      showToast('Recargando vista del informe...', 'info');
    } finally {
      // 2. Refrescar el iframe de Looker Studio para tomar los datos actualizados
      if (iframe && State.lookerUrl) {
        const cleanUrl = State.lookerUrl;
        iframe.src = 'about:blank';
        setTimeout(() => {
          iframe.src = cleanUrl;
        }, 120);
      }
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHtml || '<i data-lucide="rotate-cw"></i> <span>Recargar</span>';
        refreshIcons();
      }
      showToast('Dashboard de Looker Studio recargado', 'success');
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
    showToast('URL restablecida a la predeterminada', 'info');
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
    showToast('URL de Looker Studio guardada y aplicada', 'success');
    modal?.classList.remove('active');
  });
}



// ==============================================================================
// 5. UTILIDADES (TOAST & FORMATTERS)
// ==============================================================================
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  let iconName = 'info';
  if (type === 'success') iconName = 'check-circle';
  if (type === 'error') iconName = 'alert-triangle';

  toast.innerHTML = `
    <i data-lucide="${iconName}"></i>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  refreshIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

function formatCurrency(val) {
  const num = parseFloat(val) || 0;
  return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
