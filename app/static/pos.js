/**
 * FERROSTATS — TERMINAL DE PUNTO DE VENTA (POS ACID)
 * Aplicación de mostrador para cajeros y empleados de la ferretería.
 * Arquitectura transaccional de ultra-baja latencia (< 50ms) en SQLite WAL.
 */

const PosState = {
  products: [],
  cart: [],
  selectedCategory: '',
  searchQuery: '',
  currentUserId: 3 // Cajero por defecto (Carlos Martínez)
};

document.addEventListener('DOMContentLoaded', () => {
  initPosEvents();
  loadPosCatalog();
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
    'X-User-Role': 'CAJERO',
    'X-User-Id': String(PosState.currentUserId),
    ...(options.headers || {})
  };

  const res = await fetch(endpoint, { ...options, headers });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `Error HTTP ${res.status}`);
  }
  return data;
}

function initPosEvents() {
  const searchInput = document.getElementById('posSearchInput');
  const btnClearSearch = document.getElementById('btnClearSearch');

  searchInput?.addEventListener('input', (e) => {
    PosState.searchQuery = e.target.value.trim().toLowerCase();
    renderProductsGrid();
  });

  btnClearSearch?.addEventListener('click', () => {
    searchInput.value = '';
    PosState.searchQuery = '';
    renderProductsGrid();
    searchInput.focus();
  });

  // Filtros de categoría
  document.querySelectorAll('#posCategoryFilters .cat-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#posCategoryFilters .cat-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      PosState.selectedCategory = btn.getAttribute('data-cat') || '';
      renderProductsGrid();
    });
  });

  // Calculadora de cambio y billetes rápidos
  const cashInput = document.getElementById('posCashGiven');
  cashInput?.addEventListener('input', updateCashChange);

  // Cambio de método de pago (Efectivo vs Tarjeta vs QR)
  document.getElementById('posPaymentMethod')?.addEventListener('change', () => {
    updatePaymentMethodUI();
    refreshIcons();
  });

  // Botón monto exacto
  document.getElementById('btnExactCash')?.addEventListener('click', () => {
    const total = getCartTotal();
    const cashInput = document.getElementById('posCashGiven');
    if (cashInput) {
      cashInput.value = total.toFixed(2);
      updateCashChange();
    }
  });

  // Botones de billetes rápidos ($5, $10, $20, $50, $100)
  document.querySelectorAll('#posQuickBills .btn-bill').forEach(btn => {
    btn.addEventListener('click', () => {
      const amount = btn.getAttribute('data-amount');
      const cashInput = document.getElementById('posCashGiven');
      if (cashInput && amount) {
        cashInput.value = parseFloat(amount).toFixed(2);
        updateCashChange();
      }
    });
  });

  // Vaciar carrito
  document.getElementById('btnClearCart')?.addEventListener('click', () => {
    if (PosState.cart.length > 0) {
      PosState.cart = [];
      renderCart();
      showToast('Carrito vaciado', 'info');
    }
  });

  // Checkout
  document.getElementById('btnConfirmCheckout')?.addEventListener('click', handleCheckout);

  // Cerrar recibo
  document.getElementById('btnCloseReceipt')?.addEventListener('click', () => {
    document.getElementById('modalReceiptOverlay').classList.remove('active');
    searchInput.focus();
  });
}

async function loadPosCatalog() {
  try {
    const products = await apiFetch('/api/v1/products');
    PosState.products = products;
    renderProductsGrid();
  } catch (err) {
    showToast(`Error al cargar catálogo: ${err.message}`, 'error');
  }
}

function renderProductsGrid() {
  const grid = document.getElementById('posProductsGrid');
  grid.innerHTML = '';

  let filtered = PosState.products;

  if (PosState.selectedCategory) {
    filtered = filtered.filter(p => String(p.category_id) === PosState.selectedCategory);
  }

  if (PosState.searchQuery) {
    filtered = filtered.filter(p => 
      p.sku.toLowerCase().includes(PosState.searchQuery) ||
      p.product_name.toLowerCase().includes(PosState.searchQuery)
    );
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: #94a3b8;">
        <i data-lucide="package-search" style="width: 2.5rem; height: 2.5rem; margin-bottom: 0.5rem; color: #64748b;"></i>
        <p>No se encontraron artículos con el criterio de búsqueda.</p>
      </div>
    `;
    refreshIcons();
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement('div');
    const isAgotado = p.current_stock <= 0;
    const isBajo = p.current_stock > 0 && p.current_stock <= p.min_stock;
    
    let statusText = 'Óptimo';
    let statusClass = 'wh-status-optimo';
    let statusIcon = 'check-circle-2';

    if (isAgotado) {
      statusText = 'Agotado';
      statusClass = 'wh-status-agotado';
      statusIcon = 'alert-circle';
    } else if (isBajo) {
      statusText = 'Bajo Stock';
      statusClass = 'wh-status-reorden';
      statusIcon = 'alert-triangle';
    }

    card.className = 'pos-product-card';
    card.innerHTML = `
      <div class="pos-card-head">
        <span class="wh-sku-clean">${p.sku}</span>
        <div class="wh-status-clean ${statusClass}">
          <i data-lucide="${statusIcon}"></i>
          <span>${statusText}</span>
        </div>
      </div>
      <div class="pos-card-title">${escapeHtml(p.product_name)}</div>
      <div class="pos-card-sub">
        <span><i data-lucide="map-pin"></i> ${p.aisle_location}</span>
        <span>Stock: <strong>${p.current_stock}</strong> ${p.unit_measure}</span>
      </div>
      <div class="pos-card-foot">
        <div class="pos-card-price">$${p.unit_price_usd.toFixed(2)}</div>
        <button 
          class="btn-pos-add ${isAgotado ? 'disabled' : ''}" 
          onclick="addToCart(${p.product_id})"
          ${isAgotado ? 'disabled' : ''}
          title="${isAgotado ? 'Artículo agotado' : 'Agregar al ticket'}"
        >
          <i data-lucide="plus"></i> Agregar
        </button>
      </div>
    `;
    grid.appendChild(card);
  });

  refreshIcons();
}

function addToCart(productId) {
  const prod = PosState.products.find(p => p.product_id === productId);
  if (!prod) return;

  if (prod.current_stock <= 0) {
    showToast(`Artículo ${prod.sku} agotado.`, 'error');
    return;
  }

  const existing = PosState.cart.find(item => item.product_id === productId);
  if (existing) {
    if (existing.quantity >= prod.current_stock) {
      showToast(`Stock máximo alcanzado (${prod.current_stock} uds disponibles).`, 'error');
      return;
    }
    existing.quantity += 1;
  } else {
    PosState.cart.push({
      product_id: prod.product_id,
      sku: prod.sku,
      product_name: prod.product_name,
      unit_price_usd: prod.unit_price_usd,
      quantity: 1,
      current_stock: prod.current_stock
    });
  }

  renderCart();
}

function updateCartQty(productId, delta) {
  const item = PosState.cart.find(i => i.product_id === productId);
  if (!item) return;

  const newQty = item.quantity + delta;
  if (newQty <= 0) {
    removeFromCart(productId);
    return;
  }
  if (newQty > item.current_stock) {
    showToast(`Solo hay ${item.current_stock} unidades disponibles de ${item.sku}.`, 'error');
    return;
  }
  item.quantity = newQty;
  renderCart();
}

function removeFromCart(productId) {
  PosState.cart = PosState.cart.filter(i => i.product_id !== productId);
  renderCart();
}

function getCartTotal() {
  return PosState.cart.reduce((sum, item) => sum + (item.quantity * item.unit_price_usd), 0);
}

function renderCart() {
  const list = document.getElementById('cartItemsList');
  const btnCheckout = document.getElementById('btnConfirmCheckout');

  if (PosState.cart.length === 0) {
    list.innerHTML = `
      <div class="cart-empty-state">
        <i data-lucide="shopping-basket"></i>
        <p>El carrito está vacío</p>
        <span>Selecciona artículos del catálogo para facturar</span>
      </div>
    `;
    document.getElementById('cartSubtotal').textContent = '$0.00';
    document.getElementById('cartIva').textContent = '$0.00';
    document.getElementById('cartTotal').textContent = '$0.00';
    document.getElementById('posCashChange').textContent = '$0.00';
    
    const changeContainer = document.getElementById('posChangeContainer');
    if (changeContainer) changeContainer.classList.remove('insufficient', 'sufficient');
    const labelEl = document.getElementById('posChangeLabel');
    if (labelEl) labelEl.textContent = 'Cambio / Vuelto:';

    btnCheckout.disabled = true;
    refreshIcons();
    return;
  }

  list.innerHTML = '';
  let totalVenta = 0;

  PosState.cart.forEach(item => {
    const itemTotal = item.quantity * item.unit_price_usd;
    totalVenta += itemTotal;

    const row = document.createElement('div');
    row.className = 'cart-item-card';
    row.innerHTML = `
      <div class="cart-item-meta">
        <div class="cart-item-title" title="${escapeHtml(item.product_name)}">${item.sku} - ${escapeHtml(item.product_name)}</div>
        <div class="cart-item-price-unit">$${item.unit_price_usd.toFixed(2)} c/u</div>
      </div>
      <div class="cart-item-actions">
        <div class="qty-control">
          <button class="btn-qty" onclick="updateCartQty(${item.product_id}, -1)">-</button>
          <span class="qty-num">${item.quantity}</span>
          <button class="btn-qty" onclick="updateCartQty(${item.product_id}, 1)">+</button>
        </div>
        <div class="item-subtotal">$${itemTotal.toFixed(2)}</div>
        <button class="btn-remove-item" onclick="removeFromCart(${item.product_id})" title="Quitar">
          <i data-lucide="trash-2"></i>
        </button>
      </div>
    `;
    list.appendChild(row);
  });

  // En El Salvador los precios al consumidor son IVA incluido (13%).
  // Desglose fiscal exacto de acuerdo a la ley tributaria y al backend SQLite/BigQuery:
  const subtotalNeto = Math.round((totalVenta / 1.13) * 100) / 100;
  const iva = Math.round((totalVenta - subtotalNeto) * 100) / 100;

  document.getElementById('cartSubtotal').textContent = `$${subtotalNeto.toFixed(2)}`;
  document.getElementById('cartIva').textContent = `$${iva.toFixed(2)}`;
  document.getElementById('cartTotal').textContent = `$${totalVenta.toFixed(2)}`;
  btnCheckout.disabled = false;

  updatePaymentMethodUI();
  refreshIcons();
}

function updatePaymentMethodUI() {
  const method = document.getElementById('posPaymentMethod').value;
  const cashBox = document.getElementById('posCashBox');
  const elecBox = document.getElementById('posElectronicBox');
  const elecText = document.getElementById('posElectronicText');
  const elecIcon = document.getElementById('posElectronicIcon');
  const total = getCartTotal();

  if (method === 'EFECTIVO') {
    if (cashBox) cashBox.style.display = 'block';
    if (elecBox) elecBox.style.display = 'none';
    updateCashChange();
  } else {
    if (cashBox) cashBox.style.display = 'none';
    if (elecBox) elecBox.style.display = 'block';
    if (elecText) {
      if (method === 'TRANSFERENCIA_QR') {
        elecText.textContent = `Cobro QR Chivo / Banco por $${total.toFixed(2)} exactos`;
        if (elecIcon) elecIcon.setAttribute('data-lucide', 'qr-code');
      } else {
        elecText.textContent = `Cobro con Tarjeta Débito/Crédito por $${total.toFixed(2)} exactos`;
        if (elecIcon) elecIcon.setAttribute('data-lucide', 'credit-card');
      }
    }
  }
}

function updateCashChange() {
  const method = document.getElementById('posPaymentMethod').value;
  if (method !== 'EFECTIVO') return;

  const total = getCartTotal();
  const cashInput = document.getElementById('posCashGiven');
  const rawCash = cashInput.value.trim();
  const changeEl = document.getElementById('posCashChange');
  const labelEl = document.getElementById('posChangeLabel');
  const changeContainer = document.getElementById('posChangeContainer');

  if (!rawCash) {
    changeEl.textContent = '$0.00';
    changeEl.style.color = '#94a3b8';
    if (labelEl) labelEl.textContent = 'Cambio / Vuelto:';
    if (changeContainer) changeContainer.classList.remove('insufficient', 'sufficient');
    return;
  }

  const cashVal = parseFloat(rawCash) || 0;

  if (total <= 0) {
    changeEl.textContent = '$0.00';
    changeEl.style.color = '#94a3b8';
    if (labelEl) labelEl.textContent = 'Cambio / Vuelto:';
    if (changeContainer) changeContainer.classList.remove('insufficient', 'sufficient');
    return;
  }

  if (cashVal >= total) {
    const change = cashVal - total;
    changeEl.textContent = `$${change.toFixed(2)}`;
    changeEl.style.color = '#10b981';
    if (labelEl) labelEl.textContent = 'Cambio a Entregar:';
    if (changeContainer) {
      changeContainer.classList.remove('insufficient');
      changeContainer.classList.add('sufficient');
    }
  } else {
    const missing = total - cashVal;
    changeEl.textContent = `- $${missing.toFixed(2)}`;
    changeEl.style.color = '#ef4444';
    if (labelEl) labelEl.textContent = 'Faltan cobrar:';
    if (changeContainer) {
      changeContainer.classList.remove('sufficient');
      changeContainer.classList.add('insufficient');
    }
  }
}

async function handleCheckout() {
  if (PosState.cart.length === 0) {
    showToast('El ticket de venta está vacío', 'info');
    return;
  }

  const method = document.getElementById('posPaymentMethod').value;
  const total = getCartTotal();
  const cashInput = document.getElementById('posCashGiven');
  const rawCash = cashInput.value.trim();
  const cashGiven = parseFloat(rawCash) || 0;

  // Validación estricta para ventas en efectivo
  if (method === 'EFECTIVO') {
    if (!rawCash) {
      showToast(`Ingrese el efectivo recibido ($${total.toFixed(2)}) o presione "Exacto"`, 'error');
      cashInput.focus();
      return;
    }
    if (cashGiven < total) {
      const missing = (total - cashGiven).toFixed(2);
      showToast(`Efectivo insuficiente. Total a cobrar: $${total.toFixed(2)}, entregó: $${cashGiven.toFixed(2)} (Faltan $${missing})`, 'error');
      cashInput.focus();
      return;
    }
  }

  const btnCheckout = document.getElementById('btnConfirmCheckout');
  btnCheckout.disabled = true;
  btnCheckout.innerHTML = '<i data-lucide="loader-2" class="spin"></i> Procesando...';
  refreshIcons();

  const payload = {
    transaction_uuid: `TXN-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
    user_id: PosState.currentUserId,
    customer_type: document.getElementById('posCustomerType').value,
    payment_method: method,
    items: PosState.cart.map(i => ({
      product_id: i.product_id,
      quantity: i.quantity
    }))
  };

  try {
    const res = await apiFetch('/api/v1/pos/checkout', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    res.cash_given = method === 'EFECTIVO' ? cashGiven : total;
    res.cash_change = method === 'EFECTIVO' ? Math.max(0, cashGiven - total) : 0;

    showToast('¡Venta completada con éxito!', 'success');
    showReceiptModal(res);

    // Actualizar catálogo local
    await loadPosCatalog();
    PosState.cart = [];
    document.getElementById('posCashGiven').value = '';
    renderCart();

  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btnCheckout.disabled = false;
    btnCheckout.innerHTML = '<i data-lucide="check-circle-2"></i> <span>Cobrar y Procesar Venta</span>';
    refreshIcons();
  }
}

function showReceiptModal(txData) {
  const content = document.getElementById('receiptContent');
  if (!content || !txData) return;

  const items = txData.items_breakdown || txData.items || [];
  const totalAmount = Number(txData.total_amount_usd ?? 0);
  const subtotal = Number(txData.subtotal_usd ?? (totalAmount / 1.13));
  const iva = Number(txData.iva_usd ?? (totalAmount - subtotal));

  const itemsRows = items.map(it => {
    const qty = Number(it.quantity || 1);
    const itemSubtotal = Number(it.subtotal_usd ?? (qty * Number(it.unit_price_usd || 0)));
    return `
      <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem; font-size: 0.8rem;">
        <span>${qty}x ${escapeHtml(it.product_name || 'Artículo')}</span>
        <strong>$${itemSubtotal.toFixed(2)}</strong>
      </div>
    `;
  }).join('');

  const ticketUuid = escapeHtml(txData.transaction_uuid || `TICKET-${txData.sale_id || Date.now()}`);
  const ticketDate = escapeHtml(txData.timestamp || txData.sale_timestamp || new Date().toLocaleString());
  const cashier = escapeHtml(txData.cashier_name || `Cajero #${txData.user_id || 1}`);
  const paymentMethod = escapeHtml(txData.payment_method || 'EFECTIVO');
  const isEfectivo = paymentMethod === 'EFECTIVO';
  const cashGiven = Number(txData.cash_given ?? totalAmount);
  const cashChange = Number(txData.cash_change ?? 0);

  content.innerHTML = `
    <div class="receipt-ticket">
      <div style="text-align: center; margin-bottom: 0.75rem;">
        <div style="font-weight: 800; font-size: 0.95rem;">COMPROBANTE DE PAGO</div>
        <div style="font-size: 0.72rem; color: #94a3b8;">Sucursal Central • Terminal 01</div>
      </div>
      <div class="receipt-divider"></div>
      <div style="font-size: 0.75rem; color: #cbd5e1; margin-bottom: 0.5rem;">
        <div><strong>Ticket:</strong> ${ticketUuid}</div>
        <div><strong>Fecha:</strong> ${ticketDate}</div>
        <div><strong>Cajero:</strong> ${cashier}</div>
        <div><strong>Pago:</strong> ${paymentMethod}</div>
      </div>
      <div class="receipt-divider"></div>
      <div style="margin: 0.75rem 0;">
        ${itemsRows || '<div style="font-size: 0.75rem; color: #94a3b8; text-align: center;">Sin desglose de artículos</div>'}
      </div>
      <div class="receipt-divider"></div>
      <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 0.35rem;">
        <span>Subtotal:</span>
        <span>$${subtotal.toFixed(2)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 0.15rem;">
        <span>IVA (13%):</span>
        <span>$${iva.toFixed(2)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 1.05rem; font-weight: 800; color: #f59e0b; margin-top: 0.5rem; border-top: 1px dashed #475569; padding-top: 0.5rem;">
        <span>TOTAL COBRADO:</span>
        <span>$${totalAmount.toFixed(2)}</span>
      </div>
      ${isEfectivo ? `
      <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 0.4rem; color: #94a3b8;">
        <span>Efectivo Recibido:</span>
        <span>$${cashGiven.toFixed(2)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 0.2rem; color: #10b981; font-weight: 600;">
        <span>Cambio Entregado:</span>
        <span>$${cashChange.toFixed(2)}</span>
      </div>
      ` : `
      <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 0.4rem; color: #38bdf8;">
        <span>Modalidad:</span>
        <span>Cobro Electrónico Aprobado</span>
      </div>
      `}
      <div class="receipt-divider"></div>
      <div style="text-align: center; font-size: 0.7rem; color: #94a3b8; margin-top: 0.5rem;">
        ¡Gracias por su compra!<br>Garantía de calidad ferretera
      </div>
    </div>
  `;

  document.getElementById('modalReceiptOverlay')?.classList.add('active');
  refreshIcons();
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
