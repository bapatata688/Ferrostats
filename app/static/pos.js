/**
 * FERROSTATS — POINT-OF-SALE (POS) CASHIER TERMINAL
 * Ultra-low latency (< 50ms) ACID transactional cashier engine powered by SQLite WAL.
 * Lead Architect: Diego Alejandro Escobar Barahona
 */

const PosTranslations = {
  en: {
    langLabel: 'EN',
    activeRegister: 'Active Register',
    searchPlaceholder: 'Search SKU or product name (e.g., MC-001, Cordless Drill, PVC, Cement)...',
    allCategories: 'All Items',
    emptyCartTitle: 'Cart is empty',
    emptyCartSubtitle: 'Select products from the catalog to ring up',
    subtotal: 'Subtotal (excl. Tax)',
    tax: 'Sales Tax / VAT (13%)',
    totalDue: 'TOTAL AMOUNT DUE',
    customerLabel: 'Customer Type:',
    customerFinal: 'Retail / Final Consumer',
    customerContractor: 'General Contractor / Builder',
    customerWorkshop: 'Industrial Workshop',
    paymentLabel: 'Payment Method:',
    paymentCash: 'Cash (USD)',
    paymentQr: 'QR Transfer / Mobile',
    paymentCard: 'Debit / Credit Card',
    cashTendered: 'Cash Tendered ($):',
    exactBtn: 'Exact',
    changeDue: 'Change Due:',
    amountShort: 'Amount Due (Short):',
    completeSaleBtn: 'Complete Sale & Print Receipt',
    processingBtn: 'Processing Checkout...',
    acidGuarantee: 'Atomic ACID transaction on SQLite WAL (< 50 ms)',
    receiptModalTitle: 'Sale Confirmed Successfully',
    receiptModalSub: 'Atomic ACID Transaction Committed to SQLite WAL',
    newSaleBtn: 'New Sale / Done',
    statusOptimal: 'Optimal',
    statusLowStock: 'Low Stock',
    statusOutOfStock: 'Out of Stock',
    addBtn: 'Add',
    unitPriceEach: 'ea.',
    clearCartToast: 'Cart cleared',
    emptyTicketToast: 'Sales ticket is empty',
    cashRequiredToast: 'Please enter cash tendered ($) or click "Exact"',
    insufficientCashToast: 'Insufficient cash tendered. Total: $',
    saleSuccessToast: 'Sale completed successfully!',
    receiptTitle: 'SALES RECEIPT & TAX INVOICE',
    receiptBranch: 'Central Retail Branch • Register 01',
    receiptTicket: 'Ticket ID:',
    receiptDate: 'Date & Time:',
    receiptCashier: 'Cashier:',
    receiptPayment: 'Payment:',
    receiptTotalCharged: 'TOTAL CHARGED:',
    receiptCashTendered: 'Cash Tendered:',
    receiptChangeGiven: 'Change Returned:',
    receiptElectronicMode: 'Electronic Charge Approved (Auth #OK)',
    receiptThanks: 'Thank you for your business! • Hardware Quality Guaranteed',
    noItemsFound: 'No products found matching your search query.'
  },
  es: {
    langLabel: 'ES',
    activeRegister: 'Mostrador Activo',
    searchPlaceholder: 'Buscar SKU o nombre (ej. MC-001, Taladro, PVC, Cemento, Broca)...',
    allCategories: 'Todos los Artículos',
    emptyCartTitle: 'El carrito está vacío',
    emptyCartSubtitle: 'Selecciona artículos del catálogo para facturar',
    subtotal: 'Subtotal Gravado (sin IVA)',
    tax: 'IVA (13%)',
    totalDue: 'TOTAL A COBRAR',
    customerLabel: 'Cliente:',
    customerFinal: 'Consumidor Final',
    customerContractor: 'Contratista / Maestro Obra',
    customerWorkshop: 'Taller Industrial',
    paymentLabel: 'Método de Pago:',
    paymentCash: 'Efectivo',
    paymentQr: 'Transferencia QR',
    paymentCard: 'Tarjeta Débito/Crédito',
    cashTendered: 'Efectivo Recibido ($):',
    exactBtn: 'Exacto',
    changeDue: 'Cambio / Vuelto:',
    amountShort: 'Faltan cobrar:',
    completeSaleBtn: 'Cobrar y Procesar Venta',
    processingBtn: 'Procesando Venta...',
    acidGuarantee: 'Transacción ACID atómica en SQLite WAL (< 50 ms)',
    receiptModalTitle: 'Venta Confirmada Exitosamente',
    receiptModalSub: 'Transacción ACID Procesada en SQLite WAL',
    newSaleBtn: 'Nueva Venta / Listo',
    statusOptimal: 'Óptimo',
    statusLowStock: 'Bajo Stock',
    statusOutOfStock: 'Agotado',
    addBtn: 'Agregar',
    unitPriceEach: 'c/u',
    clearCartToast: 'Carrito vaciado',
    emptyTicketToast: 'El ticket de venta está vacío',
    cashRequiredToast: 'Ingrese el efectivo recibido ($) o presione "Exacto"',
    insufficientCashToast: 'Efectivo insuficiente. Total a cobrar: $',
    saleSuccessToast: '¡Venta completada con éxito!',
    receiptTitle: 'COMPROBANTE DE PAGO',
    receiptBranch: 'Sucursal Central • Terminal 01',
    receiptTicket: 'Ticket:',
    receiptDate: 'Fecha:',
    receiptCashier: 'Cajero:',
    receiptPayment: 'Pago:',
    receiptTotalCharged: 'TOTAL COBRADO:',
    receiptCashTendered: 'Efectivo Recibido:',
    receiptChangeGiven: 'Cambio Entregado:',
    receiptElectronicMode: 'Cobro Electrónico Aprobado',
    receiptThanks: '¡Gracias por su compra! • Garantía de calidad ferretera',
    noItemsFound: 'No se encontraron artículos con el criterio de búsqueda.'
  }
};

const PosState = {
  lang: localStorage.getItem('ferrostats_lang') || 'en',
  products: [],
  cart: [],
  selectedCategory: '',
  searchQuery: '',
  currentUserId: 3 // Default cashier (Carlos Martínez)
};

function t(key) {
  const dict = PosTranslations[PosState.lang] || PosTranslations.en;
  return dict[key] || PosTranslations.en[key] || key;
}

document.addEventListener('DOMContentLoaded', () => {
  initLanguageToggle();
  initPosEvents();
  loadPosCatalog();
  applyStaticTranslations();
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
  const btn = document.getElementById('btnPosLangToggle');
  const label = document.getElementById('posLangLabel');
  if (label) label.textContent = PosState.lang.toUpperCase();

  btn?.addEventListener('click', () => {
    PosState.lang = PosState.lang === 'en' ? 'es' : 'en';
    localStorage.setItem('ferrostats_lang', PosState.lang);
    if (label) label.textContent = PosState.lang.toUpperCase();
    applyStaticTranslations();
    renderProductsGrid();
    renderCart();
  });
}

function applyStaticTranslations() {
  const isEn = PosState.lang === 'en';
  const searchInput = document.getElementById('posSearchInput');
  if (searchInput) searchInput.placeholder = t('searchPlaceholder');

  // Customer options
  const optFinal = document.querySelector('#posCustomerType option[value="CONSUMIDOR_FINAL"]');
  const optContr = document.querySelector('#posCustomerType option[value="CONTRATISTA"]');
  const optWork = document.querySelector('#posCustomerType option[value="TALLER_INDUSTRIAL"]');
  if (optFinal) optFinal.textContent = t('customerFinal');
  if (optContr) optContr.textContent = t('customerContractor');
  if (optWork) optWork.textContent = t('customerWorkshop');

  // Payment options
  const optCash = document.querySelector('#posPaymentMethod option[value="EFECTIVO"]');
  const optQr = document.querySelector('#posPaymentMethod option[value="TRANSFERENCIA_QR"]');
  const optCard = document.querySelector('#posPaymentMethod option[value="TARJETA"]');
  if (optCash) optCash.textContent = t('paymentCash');
  if (optQr) optQr.textContent = t('paymentQr');
  if (optCard) optCard.textContent = t('paymentCard');

  // Checkout button text
  const btnCheckout = document.getElementById('btnConfirmCheckout');
  if (btnCheckout && !btnCheckout.disabled) {
    btnCheckout.innerHTML = `<i data-lucide="check-circle-2"></i> <span>${t('completeSaleBtn')}</span>`;
  }

  // Active register badge
  const badge = document.querySelector('.badge-role-cashier');
  if (badge) {
    badge.innerHTML = `<span class="pulse-dot"></span> ${t('activeRegister')}`;
  }

  refreshIcons();
}

async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Role': 'CASHIER',
    'X-User-Id': String(PosState.currentUserId),
    ...(options.headers || {})
  };

  const res = await fetch(endpoint, { ...options, headers });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `HTTP Error ${res.status}`);
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

  // Category filters
  document.querySelectorAll('#posCategoryFilters .cat-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#posCategoryFilters .cat-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      PosState.selectedCategory = btn.getAttribute('data-cat') || '';
      renderProductsGrid();
    });
  });

  // Cash change calculator
  const cashInput = document.getElementById('posCashGiven');
  cashInput?.addEventListener('input', updateCashChange);

  // Payment method switcher
  document.getElementById('posPaymentMethod')?.addEventListener('change', () => {
    updatePaymentMethodUI();
    refreshIcons();
  });

  // Exact cash button
  document.getElementById('btnExactCash')?.addEventListener('click', () => {
    const total = getCartTotal();
    const input = document.getElementById('posCashGiven');
    if (input) {
      input.value = total.toFixed(2);
      updateCashChange();
    }
  });

  // Quick bills ($5, $10, $20, $50, $100)
  document.querySelectorAll('#posQuickBills .btn-bill').forEach(btn => {
    btn.addEventListener('click', () => {
      const amount = btn.getAttribute('data-amount');
      const input = document.getElementById('posCashGiven');
      if (input && amount) {
        input.value = parseFloat(amount).toFixed(2);
        updateCashChange();
      }
    });
  });

  // Clear cart
  document.getElementById('btnClearCart')?.addEventListener('click', () => {
    if (PosState.cart.length > 0) {
      PosState.cart = [];
      renderCart();
      showToast(t('clearCartToast'), 'info');
    }
  });

  // Checkout
  document.getElementById('btnConfirmCheckout')?.addEventListener('click', handleCheckout);

  // Close receipt
  document.getElementById('btnCloseReceipt')?.addEventListener('click', () => {
    document.getElementById('modalReceiptOverlay').classList.remove('active');
    searchInput?.focus();
  });
}

async function loadPosCatalog() {
  try {
    const products = await apiFetch('/api/v1/products');
    PosState.products = products;
    renderProductsGrid();
  } catch (err) {
    showToast(`Failed to load catalog: ${err.message}`, 'error');
  }
}

function renderProductsGrid() {
  const grid = document.getElementById('posProductsGrid');
  if (!grid) return;
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
        <p>${t('noItemsFound')}</p>
      </div>
    `;
    refreshIcons();
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement('div');
    const isAgotado = p.current_stock <= 0;
    const isBajo = p.current_stock > 0 && p.current_stock <= p.min_stock;
    
    let statusText = t('statusOptimal');
    let statusClass = 'wh-status-optimo';
    let statusIcon = 'check-circle-2';

    if (isAgotado) {
      statusText = t('statusOutOfStock');
      statusClass = 'wh-status-agotado';
      statusIcon = 'alert-circle';
    } else if (isBajo) {
      statusText = t('statusLowStock');
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
          title="${isAgotado ? t('statusOutOfStock') : t('addBtn')}"
        >
          <i data-lucide="plus"></i> ${t('addBtn')}
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
    showToast(`${prod.sku} is out of stock.`, 'error');
    return;
  }

  const existing = PosState.cart.find(item => item.product_id === productId);
  if (existing) {
    if (existing.quantity >= prod.current_stock) {
      showToast(`Maximum stock reached (${prod.current_stock} units available).`, 'error');
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
    showToast(`Only ${item.current_stock} units available for ${item.sku}.`, 'error');
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
        <p>${t('emptyCartTitle')}</p>
        <span>${t('emptyCartSubtitle')}</span>
      </div>
    `;
    document.getElementById('cartSubtotal').textContent = '$0.00';
    document.getElementById('cartIva').textContent = '$0.00';
    document.getElementById('cartTotal').textContent = '$0.00';
    document.getElementById('posCashChange').textContent = '$0.00';
    
    const changeContainer = document.getElementById('posChangeContainer');
    if (changeContainer) changeContainer.classList.remove('insufficient', 'sufficient');
    const labelEl = document.getElementById('posChangeLabel');
    if (labelEl) labelEl.textContent = t('changeDue');

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
        <div class="cart-item-price-unit">$${item.unit_price_usd.toFixed(2)} ${t('unitPriceEach')}</div>
      </div>
      <div class="cart-item-actions">
        <div class="qty-control">
          <button class="btn-qty" onclick="updateCartQty(${item.product_id}, -1)">-</button>
          <span class="qty-num">${item.quantity}</span>
          <button class="btn-qty" onclick="updateCartQty(${item.product_id}, 1)">+</button>
        </div>
        <div class="item-subtotal">$${itemTotal.toFixed(2)}</div>
        <button class="btn-remove-item" onclick="removeFromCart(${item.product_id})" title="Remove item">
          <i data-lucide="trash-2"></i>
        </button>
      </div>
    `;
    list.appendChild(row);
  });

  // VAT (13%) breakdown
  const subtotalNeto = Math.round((totalVenta / 1.13) * 100) / 100;
  const iva = Math.round((totalVenta - subtotalNeto) * 100) / 100;

  document.getElementById('cartSubtotal').textContent = `$${subtotalNeto.toFixed(2)}`;
  document.getElementById('cartIva').textContent = `$${iva.toFixed(2)}`;
  document.getElementById('cartTotal').textContent = `$${totalVenta.toFixed(2)}`;
  btnCheckout.disabled = false;
  btnCheckout.innerHTML = `<i data-lucide="check-circle-2"></i> <span>${t('completeSaleBtn')}</span>`;

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

  if (method === 'EFECTIVO' || method === 'CASH') {
    if (cashBox) cashBox.style.display = 'block';
    if (elecBox) elecBox.style.display = 'none';
    updateCashChange();
  } else {
    if (cashBox) cashBox.style.display = 'none';
    if (elecBox) elecBox.style.display = 'block';
    if (elecText) {
      if (method === 'TRANSFERENCIA_QR' || method === 'QR_TRANSFER') {
        elecText.textContent = PosState.lang === 'en'
          ? `QR Mobile Transfer charge for exact $${total.toFixed(2)}`
          : `Cobro QR Chivo / Banco por $${total.toFixed(2)} exactos`;
        if (elecIcon) elecIcon.setAttribute('data-lucide', 'qr-code');
      } else {
        elecText.textContent = PosState.lang === 'en'
          ? `Debit / Credit card charge for exact $${total.toFixed(2)}`
          : `Cobro con Tarjeta Débito/Crédito por $${total.toFixed(2)} exactos`;
        if (elecIcon) elecIcon.setAttribute('data-lucide', 'credit-card');
      }
    }
  }
}

function updateCashChange() {
  const method = document.getElementById('posPaymentMethod').value;
  if (method !== 'EFECTIVO' && method !== 'CASH') return;

  const total = getCartTotal();
  const cashInput = document.getElementById('posCashGiven');
  const rawCash = cashInput.value.trim();
  const changeEl = document.getElementById('posCashChange');
  const labelEl = document.getElementById('posChangeLabel');
  const changeContainer = document.getElementById('posChangeContainer');

  if (!rawCash) {
    changeEl.textContent = '$0.00';
    changeEl.style.color = '#94a3b8';
    if (labelEl) labelEl.textContent = t('changeDue');
    if (changeContainer) changeContainer.classList.remove('insufficient', 'sufficient');
    return;
  }

  const cashVal = parseFloat(rawCash) || 0;

  if (total <= 0) {
    changeEl.textContent = '$0.00';
    changeEl.style.color = '#94a3b8';
    if (labelEl) labelEl.textContent = t('changeDue');
    if (changeContainer) changeContainer.classList.remove('insufficient', 'sufficient');
    return;
  }

  if (cashVal >= total) {
    const change = cashVal - total;
    changeEl.textContent = `$${change.toFixed(2)}`;
    changeEl.style.color = '#10b981';
    if (labelEl) labelEl.textContent = t('changeDue');
    if (changeContainer) {
      changeContainer.classList.remove('insufficient');
      changeContainer.classList.add('sufficient');
    }
  } else {
    const missing = total - cashVal;
    changeEl.textContent = `- $${missing.toFixed(2)}`;
    changeEl.style.color = '#ef4444';
    if (labelEl) labelEl.textContent = t('amountShort');
    if (changeContainer) {
      changeContainer.classList.remove('sufficient');
      changeContainer.classList.add('insufficient');
    }
  }
}

async function handleCheckout() {
  if (PosState.cart.length === 0) {
    showToast(t('emptyTicketToast'), 'info');
    return;
  }

  const method = document.getElementById('posPaymentMethod').value;
  const total = getCartTotal();
  const cashInput = document.getElementById('posCashGiven');
  const rawCash = cashInput.value.trim();
  const cashGiven = parseFloat(rawCash) || 0;

  if (method === 'EFECTIVO' || method === 'CASH') {
    if (!rawCash) {
      showToast(`${t('cashRequiredToast')} ($${total.toFixed(2)})`, 'error');
      cashInput.focus();
      return;
    }
    if (cashGiven < total) {
      const missing = (total - cashGiven).toFixed(2);
      showToast(`${t('insufficientCashToast')}${total.toFixed(2)}, received: $${cashGiven.toFixed(2)} (Missing $${missing})`, 'error');
      cashInput.focus();
      return;
    }
  }

  const btnCheckout = document.getElementById('btnConfirmCheckout');
  btnCheckout.disabled = true;
  btnCheckout.innerHTML = `<i data-lucide="loader-2" class="spin"></i> <span>${t('processingBtn')}</span>`;
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

    res.cash_given = (method === 'EFECTIVO' || method === 'CASH') ? cashGiven : total;
    res.cash_change = (method === 'EFECTIVO' || method === 'CASH') ? Math.max(0, cashGiven - total) : 0;

    showToast(t('saleSuccessToast'), 'success');
    showReceiptModal(res);

    await loadPosCatalog();
    PosState.cart = [];
    document.getElementById('posCashGiven').value = '';
    renderCart();

  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btnCheckout.disabled = false;
    btnCheckout.innerHTML = `<i data-lucide="check-circle-2"></i> <span>${t('completeSaleBtn')}</span>`;
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
        <span>${qty}x ${escapeHtml(it.product_name || 'Item')}</span>
        <strong>$${itemSubtotal.toFixed(2)}</strong>
      </div>
    `;
  }).join('');

  const ticketUuid = escapeHtml(txData.transaction_uuid || `TICKET-${txData.sale_id || Date.now()}`);
  const ticketDate = escapeHtml(txData.timestamp || txData.sale_timestamp || new Date().toLocaleString());
  const cashier = escapeHtml(txData.cashier_name || `Cashier #${txData.user_id || 1}`);
  const paymentMethod = escapeHtml(txData.payment_method || 'CASH');
  const isEfectivo = paymentMethod === 'EFECTIVO' || paymentMethod === 'CASH';
  const cashGiven = Number(txData.cash_given ?? totalAmount);
  const cashChange = Number(txData.cash_change ?? 0);

  content.innerHTML = `
    <div class="receipt-ticket">
      <div style="text-align: center; margin-bottom: 0.75rem;">
        <div style="font-weight: 800; font-size: 0.95rem;">${t('receiptTitle')}</div>
        <div style="font-size: 0.72rem; color: #94a3b8;">${t('receiptBranch')}</div>
      </div>
      <div class="receipt-divider"></div>
      <div style="font-size: 0.75rem; color: #cbd5e1; margin-bottom: 0.5rem;">
        <div><strong>${t('receiptTicket')}</strong> ${ticketUuid}</div>
        <div><strong>${t('receiptDate')}</strong> ${ticketDate}</div>
        <div><strong>${t('receiptCashier')}</strong> ${cashier}</div>
        <div><strong>${t('receiptPayment')}</strong> ${paymentMethod}</div>
      </div>
      <div class="receipt-divider"></div>
      <div style="margin: 0.75rem 0;">
        ${itemsRows || '<div style="font-size: 0.75rem; color: #94a3b8; text-align: center;">No items found</div>'}
      </div>
      <div class="receipt-divider"></div>
      <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 0.35rem;">
        <span>${t('subtotal')}:</span>
        <span>$${subtotal.toFixed(2)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 0.15rem;">
        <span>${t('tax')}:</span>
        <span>$${iva.toFixed(2)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 1.05rem; font-weight: 800; color: #f59e0b; margin-top: 0.5rem; border-top: 1px dashed #475569; padding-top: 0.5rem;">
        <span>${t('receiptTotalCharged')}</span>
        <span>$${totalAmount.toFixed(2)}</span>
      </div>
      ${isEfectivo ? `
      <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 0.4rem; color: #94a3b8;">
        <span>${t('receiptCashTendered')}</span>
        <span>$${cashGiven.toFixed(2)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 0.2rem; color: #10b981; font-weight: 600;">
        <span>${t('receiptChangeGiven')}</span>
        <span>$${cashChange.toFixed(2)}</span>
      </div>
      ` : `
      <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 0.4rem; color: #38bdf8;">
        <span>Status:</span>
        <span>${t('receiptElectronicMode')}</span>
      </div>
      `}
      <div class="receipt-divider"></div>
      <div style="text-align: center; font-size: 0.7rem; color: #94a3b8; margin-top: 0.5rem;">
        ${t('receiptThanks')}
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
