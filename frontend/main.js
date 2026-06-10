const API_URL = "http://127.0.0.1:8000";

// --- UI Navigation ---
function switchTab(tabId) {
    // Update nav buttons
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active');
    });

    // Attempt to set active class on the corresponding nav button
    const targetBtn = document.querySelector(`.nav-item[onclick*="switchTab('${tabId}')"]`);
    if (targetBtn) {
        targetBtn.classList.add('active');
        // Auto-open parent group if closed
        const parentGroup = targetBtn.closest('.nav-group');
        if (parentGroup && !parentGroup.classList.contains('open')) {
            parentGroup.classList.add('open');
        }
    } else if (typeof event !== 'undefined' && event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }

    // Update content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    const targetTab = document.getElementById(`tab-${tabId}`);
    if (targetTab) {
        targetTab.classList.add('active');
    }
}

function toggleNavGroup(headerBtn) {
    const group = headerBtn.closest('.nav-group');
    group.classList.toggle('open');
}

// --- Utils ---
const formatCurrency = (num) => {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

// --- Simulation Module ---
async function handleSimulation(e) {
    e.preventDefault();

    const btn = document.getElementById('btn-simular');
    btn.textContent = "Calculando...";
    btn.disabled = true;

    try {
        const params = new URLSearchParams({
            credito_id: 0,
            capital: document.getElementById('capital').value,
            tna_c_iva: parseFloat(document.getElementById('tna').value) / 100,
            plazo: document.getElementById('plazo').value,
            fecha_emision: document.getElementById('fecha').value,
            dia_vencimiento: document.getElementById('vto').value,
            gracia: document.getElementById('gracia').value,
            tasa_iva: document.getElementById('iva').value,
            dia_corte: 28
        });

        const res = await fetch(`${API_URL}/simular-cuotas?${params}`);
        if (!res.ok) throw new Error("Error en la simulación");

        const data = await res.json();
        renderSimulationTable(data);

        // Show summary pills
        const sumPills = document.getElementById('sim-summary');
        const totalPagado = data.reduce((acc, c) => acc + c.capital + c.interes + c.iva, 0);
        sumPills.style.display = "flex";
        sumPills.innerHTML = `
            <div class="pill">Cuotas: ${data.length}</div>
            <div class="pill">Total a Pagar: ${formatCurrency(totalPagado)}</div>
        `;

    } catch (error) {
        alert("Ocurrió un error al simular: " + error.message);
    } finally {
        btn.textContent = "Generar Cronograma";
        btn.disabled = false;
    }
}

function renderSimulationTable(cuotas) {
    const tbody = document.querySelector('#table-sim tbody');
    tbody.innerHTML = '';

    cuotas.forEach(c => {
        const total = c.capital + c.interes + c.iva;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${c.nro_cuota}</td>
            <td>${c.fecha_vencimiento}</td>
            <td>${formatCurrency(c.capital)}</td>
            <td>${formatCurrency(c.interes)}</td>
            <td>${formatCurrency(c.iva)}</td>
            <td style="font-weight: 600; color: var(--accent-primary)">${formatCurrency(total)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Balances Module ---

async function handleBalances(e) {
    e.preventDefault();

    const btn = document.getElementById('btn-balances');
    btn.textContent = "Consultando...";
    btn.disabled = true;

    try {
        const fecha = document.getElementById('bal-fecha').value;
        const activeGroups = [];
        if (document.getElementById('grp-clientes').checked) activeGroups.push({ id: 'CUIL Cliente', label: 'Cliente' });
        if (document.getElementById('grp-carteras').checked) activeGroups.push({ id: 'ID Cartera', label: 'Cartera' });
        if (document.getElementById('grp-socios').checked) activeGroups.push({ id: 'Proveedor', label: 'Proveedor/Socio' });
        if (document.getElementById('grp-originador').checked) activeGroups.push({ id: 'Originador', label: 'Originador' });
        if (document.getElementById('grp-vencimientos').checked) activeGroups.push({ id: 'Fecha Vencimiento', label: 'Vencimiento' });
        if (document.getElementById('grp-dueno').checked) activeGroups.push({ id: 'Dueño', label: 'Dueño' });
        if (document.getElementById('grp-recurso').checked) activeGroups.push({ id: 'recurso', label: 'Recurso' });
        if (document.getElementById('grp-iva').checked) activeGroups.push({ id: 'iva_operado', label: 'Tasa IVA' });

        const isGrouping = activeGroups.length > 0;

        let params = new URLSearchParams();
        if (fecha) params.append('fecha', fecha);

        if (!document.getElementById('bal-con-saldo').checked) {
            params.append('con_saldo', 'false');
        }

        const propiasVal = document.getElementById('bal-propias').value;
        if (propiasVal !== "") {
            params.append('propias', propiasVal);
        }

        if (isGrouping) {
            params.append('agrupar', 'true');
            if (document.getElementById('grp-clientes').checked) params.append('clientes', 'true');
            if (document.getElementById('grp-carteras').checked) params.append('carteras', 'true');
            if (document.getElementById('grp-socios').checked) params.append('socios', 'true');
            if (document.getElementById('grp-originador').checked) params.append('originador', 'true');
            if (document.getElementById('grp-vencimientos').checked) params.append('vencimientos', 'true');
            if (document.getElementById('grp-dueno').checked) params.append('dueño', 'true');
            if (document.getElementById('grp-recurso').checked) params.append('recurso', 'true');
            if (document.getElementById('grp-iva').checked) params.append('iva', 'true');
        }

        const res = await fetch(`${API_URL}/api/v1/reports/balances?${params}`);
        if (!res.ok) throw new Error("Error en el reporte de saldos");

        const data = await res.json();
        const reportDateObj = fecha ? new Date(fecha + 'T00:00:00') : new Date();
        renderBalancesTable(data, activeGroups, reportDateObj);

    } catch (error) {
        alert("Ocurrió un error al consultar saldos: " + error.message);
    } finally {
        btn.textContent = "Consultar Reporte";
        btn.disabled = false;
    }
}

function renderBalancesTable(data, activeGroups, reportDate) {
    const thead = document.getElementById('bal-headers');
    const tbody = document.querySelector('#table-bal tbody');
    tbody.innerHTML = '';

    // Mostrar el contenedor de la tabla
    document.getElementById('balances-results').style.display = "block";

    // Limpiar memoria de filtros
    excelFilters = {};

    const isGrouping = activeGroups && activeGroups.length > 0;

    // Configurar columnas según agrupación
    let headers = [];
    if (isGrouping) {
        headers = activeGroups.map(g => g.label).concat(["Capital", "Interés", "IVA", "Total Saldo"]);
    } else {
        headers = ["ID Crédito", "Proveedor", "Originador", "Cliente CUIL", "Cartera", "Nro. Cuota", "Fecha Vencimiento", "Capital", "Interés", "IVA", "Total Saldo"];
    }

    let theadHtml = "<tr>";
    headers.forEach((h, i) => {
        theadHtml += `<th>
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                <span>${h}</span>
                <span class="filter-icon filter-icon-table-bal" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-bal', 'bal-headers')">▼</span>
            </div>
        </th>`;
    });
    theadHtml += "</tr>";
    thead.innerHTML = theadHtml;

    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${headers.length}" class="text-center empty-state">No se encontraron saldos.</td></tr>`;
        return;
    }

    if (isGrouping) {
        data.forEach(row => {
            let colorTotal = "var(--accent-secondary)";
            if (row['Fecha Vencimiento']) {
                const vto = new Date(row['Fecha Vencimiento'] + 'T00:00:00');
                const cutoff = new Date(reportDate);
                cutoff.setHours(0, 0, 0, 0);
                if (vto < cutoff) colorTotal = "var(--error)";
            }

            const tr = document.createElement('tr');
            let html = "";

            // Build dynamic columns for each selected group
            activeGroups.forEach(g => {
                const val = (row[g.id] !== undefined && row[g.id] !== null) ? row[g.id] : '-';
                html += `<td>${val}</td>`;
            });

            // Add fixed financial columns
            html += `
                <td>${formatCurrency(row.Capital || 0)}</td>
                <td>${formatCurrency(row['Interés'] || 0)}</td>
                <td>${formatCurrency(row.IVA || 0)}</td>
                <td style="font-weight: 600; color: ${colorTotal}">${formatCurrency(row.Total || 0)}</td>
            `;
            tr.innerHTML = html;
            tbody.appendChild(tr);
        });
    } else {
        data.forEach(row => {
            let colorTotal = "var(--accent-secondary)";
            if (row['Fecha Vencimiento']) {
                const vto = new Date(row['Fecha Vencimiento'] + 'T00:00:00');
                const cutoff = new Date(reportDate);
                cutoff.setHours(0, 0, 0, 0);
                if (vto < cutoff) colorTotal = "var(--error)";
            }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row['ID Credito'] || '-'}</td>
                <td>${row.Proveedor || '-'}</td>
                <td>${row.Originador || '-'}</td>
                <td>${row['CUIL Cliente'] || '-'}</td>
                <td>${row['ID Cartera'] || '-'}</td>
                <td>${row['Nro. Cuota'] || '-'}</td>
                <td>${row['Fecha Vencimiento'] || '-'}</td>
                <td>${formatCurrency(row.Capital || 0)}</td>
                <td>${formatCurrency(row['Interés'] || 0)}</td>
                <td>${formatCurrency(row.IVA || 0)}</td>
                <td style="font-weight: 600; color: ${colorTotal}">${formatCurrency(row.Total || row.total || 0)}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

// -------------------------------------------------------------------
// Funcionalidad de Filtros Tipo Excel
// -------------------------------------------------------------------
let excelFilters = {
    'table-bal': {},
    'table-clientes': {}
};

function getUniqueValuesForCol(tableId, colIndex) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    const trs = tbody.getElementsByTagName("tr");
    const vals = new Set();
    for (let i = 0; i < trs.length; i++) {
        if (trs[i].classList.contains('sub-row')) continue;
        const td = trs[i].getElementsByTagName("td")[colIndex];
        if (td) vals.add(td.textContent.trim());
    }
    return Array.from(vals).sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
}

function openExcelFilter(e, colIndex, tableId = 'table-bal', headerId = 'bal-headers') {
    e.stopPropagation();
    closeExcelFilter();

    const uniqueValues = getUniqueValuesForCol(tableId, colIndex);
    const th = document.querySelectorAll(`#${headerId} th`)[colIndex];
    const colName = th ? th.querySelector("span").textContent.trim().toLowerCase() : "";
    const isDateCol = colName.includes("fecha") || colName.includes("vencimiento") || colName.includes("alta");

    if (!excelFilters[tableId]) excelFilters[tableId] = {};
    const filterState = excelFilters[tableId][colIndex] || { isDate: isDateCol, desde: '', hasta: '', allowedSet: new Set(uniqueValues) };
    const currentlySelected = filterState.allowedSet;

    const popover = document.createElement("div");
    popover.id = "excel-filter-popover";
    popover.className = "filter-popover glass-panel fade-in";
    popover.style.zIndex = "99999";

    let html = `
        <div style="display: flex; gap: 8px; margin-bottom: 8px;">
            <button class="btn-secondary" style="font-size: 11px; flex: 1; padding: 4px;" onclick="sortExcelFilter(event, ${colIndex}, '${tableId}', 'asc')">↑ Ascendente</button>
            <button class="btn-secondary" style="font-size: 11px; flex: 1; padding: 4px;" onclick="sortExcelFilter(event, ${colIndex}, '${tableId}', 'desc')">↓ Descendente</button>
        </div>
        <div style="margin-bottom: 8px;">
            <input type="text" id="excel-filter-search" placeholder="🔍 Buscar..." 
                style="width: 100%; padding: 6px; font-size: 12px; background: rgba(0,0,0,0.5); border: 1px solid var(--border-color); color: white; border-radius: 4px;">
        </div>
    `;

    if (isDateCol) {
        html += `
        <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px;">
            <div>
                <label style="font-size: 10px; color: var(--text-secondary); margin-bottom: 4px; display: block;">Desde (>=)</label>
                <input type="date" id="excel-filter-desde" value="${filterState.desde}" style="width: 100%; padding: 4px; font-size: 11px; background: rgba(0,0,0,0.5); border: 1px solid var(--border-color); color: white; border-radius: 4px;">
            </div>
            <div>
                <label style="font-size: 10px; color: var(--text-secondary); margin-bottom: 4px; display: block;">Hasta (<=)</label>
                <input type="date" id="excel-filter-hasta" value="${filterState.hasta}" style="width: 100%; padding: 4px; font-size: 11px; background: rgba(0,0,0,0.5); border: 1px solid var(--border-color); color: white; border-radius: 4px;">
            </div>
        </div>
        `;
    }

    html += `
        <div class="filter-popover-list" id="excel-filter-list">
            <label style="font-weight: 600; margin-bottom: 6px;">
                <input type="checkbox" id="excel-filter-all" ${currentlySelected.size === uniqueValues.length ? 'checked' : ''}>
                (Seleccionar Todo)
            </label>
            <hr style="border:0; border-top: 1px solid var(--border-color); margin: 6px 0;">
    `;

    uniqueValues.forEach(val => {
        const isChecked = currentlySelected.has(val) ? 'checked' : '';
        const displayVal = val || "(Vacío)";
        html += `
            <label class="excel-val-label" style="display: flex; gap: 6px; align-items: center; margin-bottom: 4px;">
                <input type="checkbox" class="excel-val-cb" value="${val.replace(/"/g, '&quot;')}" ${isChecked}>
                <span>${displayVal}</span>
            </label>
        `;
    });

    html += `
        </div>
        <div class="filter-popover-actions">
            <button class="btn-primary" style="font-size: 12px; padding: 6px 12px; flex-grow: 1;" onclick="applyExcelFilter(${colIndex}, '${tableId}', '${headerId}')">Aceptar</button>
            <button class="btn-secondary" style="font-size: 12px; padding: 6px 12px;" onclick="closeExcelFilter()">Cancelar</button>
        </div>
    `;

    popover.innerHTML = html;
    document.body.appendChild(popover);

    // Posicionamiento
    const rect = e.target.getBoundingClientRect();
    popover.style.left = `${rect.left + window.scrollX}px`;
    popover.style.top = `${rect.bottom + window.scrollY + 8}px`;

    // Interactividad
    const searchInput = document.getElementById("excel-filter-search");
    searchInput.addEventListener("input", (ev) => {
        const q = ev.target.value.toLowerCase();
        document.querySelectorAll(".excel-val-label").forEach(lbl => {
            const txt = lbl.textContent.toLowerCase();
            lbl.style.display = txt.includes(q) ? "flex" : "none";
        });
    });

    document.getElementById("excel-filter-all").addEventListener("change", (ev) => {
        const checked = ev.target.checked;
        document.querySelectorAll(".excel-val-cb").forEach(cb => {
            if (cb.closest('label').style.display !== 'none') {
                cb.checked = checked;
            }
        });
    });
}


window.sortExcelFilter = function (e, colIndex, tableId, direction) {
    e.stopPropagation();
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;

    // Convert NodeList to Array
    const trs = Array.from(tbody.children);
    const groups = [];
    let currentGroup = null;

    trs.forEach(tr => {
        if (tr.classList.contains('sub-row')) {
            if (currentGroup) currentGroup.subRows.push(tr);
        } else {
            currentGroup = { mainRow: tr, subRows: [] };
            groups.push(currentGroup);
        }
    });

    const parseNumeric = (val) => {
        if (!val || val === '-') return 0;
        let clean = val.replace(/[$%\s]/g, '').replace(/\./g, '').replace(',', '.');
        const num = parseFloat(clean);
        return isNaN(num) ? val : num;
    };

    groups.sort((a, b) => {
        const aCol = a.mainRow.children[colIndex];
        const bCol = b.mainRow.children[colIndex];
        if (!aCol || !bCol) return 0;

        let aVal = aCol.textContent.trim();
        let bVal = bCol.textContent.trim();

        let aNum = parseNumeric(aVal);
        let bNum = parseNumeric(bVal);

        if (typeof aNum === 'string' && aVal.match(/^\d{4}-\d{2}-\d{2}$/)) {
            aNum = new Date(aVal).getTime();
            bNum = new Date(bVal).getTime();
        }

        if (aNum === bNum) return 0;

        let comparison = 0;
        if (typeof aNum === 'number' && typeof bNum === 'number') {
            comparison = aNum > bNum ? 1 : -1;
        } else {
            comparison = aVal.localeCompare(bVal, undefined, { numeric: true });
        }

        return direction === 'asc' ? comparison : -comparison;
    });

    groups.forEach(g => {
        tbody.appendChild(g.mainRow);
        g.subRows.forEach(sr => tbody.appendChild(sr));
    });

    closeExcelFilter();
};

function closeExcelFilter() {
    const popover = document.getElementById("excel-filter-popover");
    if (popover) popover.remove();
}

function applyExcelFilter(colIndex, tableId, headerId) {
    const selected = new Set();
    document.querySelectorAll(".excel-val-cb:checked").forEach(cb => {
        selected.add(cb.value);
    });

    let desde = '';
    let hasta = '';
    let isDate = false;

    const elDesde = document.getElementById('excel-filter-desde');
    const elHasta = document.getElementById('excel-filter-hasta');
    if (elDesde || elHasta) {
        isDate = true;
        if (elDesde) desde = elDesde.value;
        if (elHasta) hasta = elHasta.value;
    }

    const totalCheckboxes = document.querySelectorAll(".excel-val-cb").length;
    if (selected.size === totalCheckboxes && !desde && !hasta) {
        delete excelFilters[tableId][colIndex];
    } else {
        excelFilters[tableId][colIndex] = { isDate, desde, hasta, allowedSet: selected };
    }

    closeExcelFilter();
    runAllExcelFilters(tableId, headerId);
}

function runAllExcelFilters(tableId, headerId) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;
    const trs = tbody.getElementsByTagName("tr");

    let lastMainRowMatch = true;
    for (let i = 0; i < trs.length; i++) {
        let tr = trs[i];
        if (tr.classList.contains('sub-row')) {
            tr.style.display = lastMainRowMatch ? "" : "none";
            continue;
        }

        let rowMatch = true;
        const tds = tr.getElementsByTagName("td");

        for (const [colIndexStr, filterObj] of Object.entries(excelFilters[tableId] || {})) {
            const colIndex = parseInt(colIndexStr);
            if (tds[colIndex]) {
                const txtValue = tds[colIndex].textContent.trim();
                let match = true;

                if (filterObj.isDate && txtValue !== '-' && txtValue !== '') {
                    const dateVal = new Date(txtValue + 'T00:00:00');
                    if (filterObj.desde) {
                        const desde = new Date(filterObj.desde + 'T00:00:00');
                        if (dateVal < desde) match = false;
                    }
                    if (filterObj.hasta) {
                        const hasta = new Date(filterObj.hasta + 'T00:00:00');
                        if (dateVal > hasta) match = false;
                    }
                }

                // Si pasamos el filtro de fecha, validamos los checkboxes (por si destildó alguno manualmente)
                if (match && !filterObj.allowedSet.has(txtValue)) {
                    match = false;
                }

                if (!match) {
                    rowMatch = false;
                    break;
                }
            }
        }
        lastMainRowMatch = rowMatch;
        tr.style.display = rowMatch ? "" : "none";
    }

    document.querySelectorAll(`.filter-icon-${tableId}`).forEach(icon => {
        const col = icon.getAttribute("data-col");
        if (excelFilters[tableId] && excelFilters[tableId][col]) {
            icon.classList.add("active");
            icon.style.color = "var(--accent-primary)";
        } else {
            icon.classList.remove("active");
            icon.style.color = "inherit";
        }
    });
}

// Cerrar clickeando afuera
document.addEventListener("click", (e) => {
    if (!e.target.closest(".filter-popover") && !e.target.closest(".filter-icon")) {
        closeExcelFilter();
    }
});

// Global Input Formatting
document.addEventListener('input', function (e) {
    if (e.target.tagName === 'INPUT' && e.target.type === 'text') {
        const start = e.target.selectionStart;
        const end = e.target.selectionEnd;
        e.target.value = e.target.value.toUpperCase();
        e.target.setSelectionRange(start, end);
    }
});

// Init
document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('fecha').valueAsDate = new Date();
    document.getElementById('bal-fecha').valueAsDate = new Date();

    try {
        const resProv = await fetch(`${API_URL}/api/v1/auxiliares/provincias`);
        if (resProv.ok) {
            const provincias = await resProv.json();
            const selectProv = document.getElementById('cli-provincia');
            const selectUpdProv = document.getElementById('upd-cli-provincia');
            provincias.forEach(p => {
                selectProv.innerHTML += `<option value="${p.id}">${p.nombre}</option>`;
                if (selectUpdProv) selectUpdProv.innerHTML += `<option value="${p.id}">${p.nombre}</option>`;
            });
        }

        const resEmp = await fetch(`${API_URL}/api/v1/auxiliares/empleadores`);
        if (resEmp.ok) {
            const empleadores = await resEmp.json();
            window.empleadoresDataCache = empleadores;
            const selectEmp = document.getElementById('cli-empleador');
            const selectUpdEmp = document.getElementById('upd-cli-empleador');
            empleadores.forEach(e => {
                selectEmp.innerHTML += `<option value="${e.id}">${e.razon_social} ${e.cuit ? `(CUIT: ${e.cuit})` : ''}</option>`;
                if (selectUpdEmp) selectUpdEmp.innerHTML += `<option value="${e.id}">${e.razon_social} ${e.cuit ? `(CUIT: ${e.cuit})` : ''}</option>`;
            });
        }

        const resSocios = await fetch(`${API_URL}/api/v1/auxiliares/socios`);
        if (resSocios.ok) {
            const socios = await resSocios.json();
            window.sociosDataCache = socios;
            const selectSocio = document.getElementById('cred-socio');
            if (selectSocio) {
                socios.forEach(s => {
                    selectSocio.innerHTML += `<option value="${s.id}">${s.razon_social} ${s.cuit ? `(CUIT: ${s.cuit})` : ''}</option>`;
                });
            }
        }

        const resTasas = await fetch(`${API_URL}/api/v1/auxiliares/tasas_y_comisiones`);
        if (resTasas.ok) {
            window.tasasDataCache = await resTasas.json();
        }
    } catch (e) {
        console.error("Error cargando listas desplegables:", e);
    }

    // Set default values for other forms
    const credEmision = document.getElementById('cred-emision');
    if (credEmision) {
        credEmision.valueAsDate = new Date();
    }

    // Handle initial hash routing
    if (window.location.hash) {
        let hashStr = window.location.hash;
        let queryParams = new URLSearchParams();
        if (hashStr.includes('?')) {
            const parts = hashStr.split('?');
            hashStr = parts[0];
            queryParams = new URLSearchParams(parts[1]);
        }

        const targetBtn = document.querySelector(`.nav-item[href="${hashStr}"]`);
        
        if (queryParams.has('cliente') && hashStr === '#listado-creditos') {
            setTimeout(() => {
                if (targetBtn) targetBtn.classList.add('active');
                viewClientCredits(queryParams.get('cliente'));
            }, 50);
        } else if (queryParams.has('cta_cte') && hashStr === '#listado-clientes') {
            setTimeout(() => {
                if (targetBtn) targetBtn.click();
                viewClientCuentaCorriente(queryParams.get('cta_cte'));
            }, 50);
        } else if (queryParams.has('credito_cta') && hashStr === '#listado-creditos') {
            setTimeout(() => {
                if (targetBtn) targetBtn.click();
                viewCreditoCuotas(queryParams.get('credito_cta'));
            }, 50);
        } else if (queryParams.has('edit') && hashStr === '#clientes') {
            setTimeout(() => {
                editCliente(queryParams.get('edit'));
            }, 50);
        } else if (targetBtn) {
            setTimeout(() => targetBtn.click(), 50);
        }
    }
});

// -------------------------------------------------------------
// Clientes Logic
// -------------------------------------------------------------
let editingClienteCuil = null;

function cancelEditCliente() {
    editingClienteCuil = null;
    document.getElementById('cliente-form').reset();
    document.getElementById('form-cliente-title').textContent = "Registro de Nuevo Cliente";
    document.getElementById('form-cliente-subtitle').textContent = "Dé de alta a un nuevo prospecto o cliente en la base centralizada del sistema.";
    document.getElementById('btn-save-cliente').textContent = "Guardar Cliente";
    document.getElementById('btn-cancel-cliente').style.display = "none";
    document.getElementById('cli-cuil').disabled = false;
    document.getElementById('cli-feedback').textContent = "";
}

async function handleClientSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-save-cliente');
    const feedback = document.getElementById('cli-feedback');

    btn.disabled = true;
    btn.textContent = "Guardando...";
    feedback.textContent = "";

    const getVal = (id) => {
        const el = document.getElementById(id);
        if (!el) return null;
        const val = el.value.trim();
        return val === "" ? null : val;
    };

    const getNum = (id) => {
        const el = document.getElementById(id);
        if (!el) return null;
        const val = el.value.trim();
        return val === "" ? null : Number(val);
    };

    const payload = {
        cuil: getVal('cli-cuil'),
        documento: getVal('cli-documento'),
        nombre: getVal('cli-nombre'),
        apellido: getVal('cli-apellido'),
        fecha_nacimiento: getVal('cli-nacimiento'),
        sexo: getVal('cli-sexo'),
        estado_civil: getVal('cli-estcivil'),
        nacionalidad: getVal('cli-nacionalidad'),
        telefono: getVal('cli-telefono'),
        telefono_2: getVal('cli-telefono2'),
        mail: getVal('cli-mail'),
        calle: getVal('cli-calle'),
        calle_nro: getNum('cli-callenro'),
        piso: getVal('cli-piso'),
        depto: getVal('cli-depto'),
        localidad: getVal('cli-localidad'),
        id_codigo_postal: getVal('cli-cp'),
        id_provincia: getNum('cli-provincia'),
        remuneracion: getNum('cli-remuneracion') || 0.0,
        legajo: getVal('cli-legajo'),
        empleador_id: getNum('cli-empleador'),
        cbu: getVal('cli-cbu')
    };

    try {
        const method = editingClienteCuil ? 'PUT' : 'POST';
        const url = editingClienteCuil ? `${API_URL}/api/v1/clientes/${editingClienteCuil}` : `${API_URL}/api/v1/clientes`;

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok) {
            feedback.style.color = "var(--accent-secondary)";
            feedback.textContent = editingClienteCuil ? "¡Cliente actualizado con éxito!" : "¡Cliente registrado con éxito!";
            if (editingClienteCuil) {
                cancelEditCliente();
                loadClientesTable(); // Update the list in background
            } else {
                document.getElementById('cliente-form').reset();
            }
        } else {
            feedback.style.color = "var(--error)";
            feedback.textContent = data.detail || "Ocurrió un error al guardar el cliente.";
        }
    } catch (error) {
        feedback.style.color = "var(--error)";
        feedback.textContent = "Error de red al conectar con el servidor.";
    } finally {
        btn.disabled = false;
        btn.textContent = editingClienteCuil ? "Actualizar Cliente" : "Guardar Cliente";
    }
}

async function editCliente(cuil) {
    try {
        const res = await fetch(`${API_URL}/api/v1/clientes/${cuil}`);
        if (!res.ok) throw new Error("No se pudieron obtener los datos del cliente.");
        const data = await res.json();

        editingClienteCuil = cuil;

        document.getElementById('form-cliente-title').textContent = `Modificando Cliente: ${data.nombre} ${data.apellido}`;
        document.getElementById('form-cliente-subtitle').textContent = `CUIL: ${cuil}`;
        document.getElementById('btn-save-cliente').textContent = "Actualizar Cliente";
        document.getElementById('btn-cancel-cliente').style.display = "inline-block";
        document.getElementById('cli-cuil').disabled = true; // CUIL cannot be changed as it is PK

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val !== null && val !== undefined ? val : "";
        };

        setVal('cli-cuil', data.cuil);
        setVal('cli-documento', data.documento);
        setVal('cli-nombre', data.nombre);
        setVal('cli-apellido', data.apellido);
        setVal('cli-nacimiento', data.fecha_nacimiento);
        setVal('cli-sexo', data.sexo);
        setVal('cli-estcivil', data.estado_civil);
        setVal('cli-nacionalidad', data.nacionalidad);
        setVal('cli-telefono', data.telefono);
        setVal('cli-telefono2', data.telefono_2);
        setVal('cli-mail', data.mail);
        setVal('cli-calle', data.calle);
        setVal('cli-callenro', data.calle_nro);
        setVal('cli-piso', data.piso);
        setVal('cli-depto', data.depto);
        setVal('cli-localidad', data.localidad);
        setVal('cli-cp', data.id_codigo_postal);
        setVal('cli-provincia', data.id_provincia);
        setVal('cli-remuneracion', data.remuneracion);
        setVal('cli-legajo', data.legajo);
        setVal('cli-empleador', data.empleador_id);
        setVal('cli-cbu', data.cbu);

        switchTab('clientes');

    } catch (e) {
        alert(e.message);
    }
}

async function deleteCliente(cuil) {
    if (!confirm(`¿Estás seguro de que deseas eliminar permanentemente el cliente con CUIL ${cuil}?`)) return;

    try {
        const res = await fetch(`${API_URL}/api/v1/clientes/${cuil}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (res.ok) {
            alert("Cliente eliminado con éxito.");
            loadClientesTable();
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (e) {
        alert("Ocurrió un error al eliminar el cliente.");
    }
}

// -------------------------------------------------------------
// Tablas Auxiliares Logic
// -------------------------------------------------------------
const AUX_SCHEMAS = {
    provincias: {
        nombre: { type: 'text', label: 'Nombre de Provincia', required: true }
    },
    empleadores: {
        cuit: { type: 'text', label: 'CUIT (Sin guiones, Opcional)' },
        razon_social: { type: 'text', label: 'Razón Social', required: true },
        es_pasivo: { type: 'checkbox', label: 'Es Pasivo (Jubilado/Pensionado)' },
        socio_comercial_id: { type: 'select_socio', label: 'Socio Comercial Asociado' }
    },
    socios: {
        razon_social: { type: 'text', label: 'Razón Social', required: true },
        cuit: { type: 'text', label: 'CUIT (Sin guiones)', required: true },
        domicilio_legal: { type: 'text', label: 'Domicilio Legal' },
        contacto_nombre: { type: 'text', label: 'Nombre de Contacto' },
        mail: { type: 'email', label: 'Email' },
        telefono: { type: 'text', label: 'Teléfono' },
        dia_corte: { type: 'number', label: 'Día de Corte', default: 28 }
    },
    tasas_y_comisiones: {
        fecha: { type: 'date', label: 'Fecha', required: true },
        estado: { type: 'text', label: 'Estado', default: 'ACTIVA', required: true },
        socio_originador_id: { type: 'select_socio', label: 'Socio Originador', required: true },
        socio_intermediario_id: { type: 'select_socio', label: 'Socio Intermediario', required: true },
        plazo: { type: 'number', label: 'Plazo (Meses)', default: 12, required: true },
        tna_c_iva: { type: 'number', label: 'TNA (con IVA)', default: 0.0, required: true },
        colocacion_originador: { type: 'number', label: '% Colocación Originador', default: 0.0, required: true },
        colocacion_intermediario: { type: 'number', label: '% Colocación Intermediario', default: 0.0, required: true },
        cobranza_originador: { type: 'number', label: '% Cobranza Originador', default: 0.0, required: true },
        cobranza_intermediario: { type: 'number', label: '% Cobranza Intermediario', default: 0.0, required: true },
        colocacion_propia: { type: 'number', label: '% Colocación Propia', default: 0.0, required: true }
    }
};

let currentAuxTable = null;
let currentAuxData = [];
let editingAuxId = null;

async function loadAuxTable() {
    const select = document.getElementById('aux-table-select');
    const table = select.value;
    if (!table) return;

    currentAuxTable = table;
    document.getElementById('btn-new-aux').disabled = false;

    const tbody = document.getElementById('aux-table-body');
    const thead = document.getElementById('aux-table-head');

    tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">Cargando...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/api/v1/auxiliares/${table}`);
        if (!res.ok) throw new Error("Error al cargar datos");
        const data = await res.json();
        currentAuxData = data;

        if (data.length === 0) {
            thead.innerHTML = '';
            tbody.innerHTML = '<tr><td colspan="100%" class="empty-state">No hay registros cargados en esta tabla.</td></tr>';
            return;
        }

        excelFilters['aux-table'] = {};

        const keys = Object.keys(data[0]);
        thead.innerHTML = `<tr>${keys.map((k, i) => {
            let title = k.replace(/_id$/g, '').replace(/_/g, ' ').toUpperCase();
            if (title === 'TNA C IVA') title = 'TNA C/IVA';
            return `<th>
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                    <span>${title}</span>
                    <span class="filter-icon filter-icon-aux-table" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'aux-table', 'aux-table-head')">▼</span>
                </div>
            </th>`;
        }).join('')}<th>ACCIONES</th></tr>`;

        tbody.innerHTML = data.map(row => {
            return `<tr>
                ${keys.map(k => {
                let val = row[k] !== null ? row[k] : '-';

                if (val !== '-' && k.includes('socio') && k.endsWith('_id') && window.sociosDataCache) {
                    // Force comparison as string/number safely
                    const socio = window.sociosDataCache.find(s => String(s.id) === String(val));
                    if (socio) val = socio.razon_social;
                }

                if (val !== '-' && (k.startsWith('colocacion_') || k.startsWith('cobranza_') || k === 'tna_c_iva')) {
                    val = Number(val).toFixed(2) + '%';
                }
                return `<td>${val}</td>`;
            }).join('')}
                <td><button class="btn-secondary" style="padding:4px 8px; font-size:12px;" onclick="openAuxModal(${row.id})">Editar</button></td>
            </tr>`;
        }).join('');

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="100%" class="empty-state" style="color:var(--error);">${e.message}</td></tr>`;
    }
}

function openAuxModal(id = null) {
    if (!currentAuxTable) return;
    editingAuxId = id;

    let record = null;
    if (id !== null) {
        record = currentAuxData.find(r => r.id === id);
    }

    const schema = AUX_SCHEMAS[currentAuxTable];
    const fieldsContainer = document.getElementById('aux-form-fields');
    fieldsContainer.innerHTML = '';

    Object.entries(schema).forEach(([key, config]) => {
        const requiredAttr = config.required ? 'required' : '';
        let value = config.default !== undefined ? config.default : '';
        if (record && record[key] !== null && record[key] !== undefined) {
            value = record[key];
        }

        let fieldHtml = "";

        if (config.type === 'select_socio') {
            let optionsHtml = '<option value="">Seleccione...</option>';
            if (window.sociosDataCache) {
                window.sociosDataCache.forEach(s => {
                    const selected = String(s.id) === String(value) ? 'selected' : '';
                    optionsHtml += `<option value="${s.id}" ${selected}>${s.razon_social} ${s.cuit ? `(CUIT: ${s.cuit})` : ''}</option>`;
                });
            }
            fieldHtml = `<select id="aux-${key}" ${requiredAttr}>${optionsHtml}</select>`;
        } else if (config.type === 'checkbox') {
            const checkedAttr = value ? 'checked' : '';
            fieldHtml = `<input type="checkbox" id="aux-${key}" style="width: auto; margin-right: 8px;" ${checkedAttr}>`;
        } else {
            const stepAttr = config.type === 'number' ? 'step="any"' : '';
            fieldHtml = `<input type="${config.type}" id="aux-${key}" value="${value}" ${requiredAttr} ${stepAttr}>`;
        }

        let groupStyle = config.type === 'checkbox' ? 'display: flex; align-items: center;' : '';
        fieldsContainer.innerHTML += `
            <div class="form-group" style="margin-bottom:0; ${groupStyle}">
                ${config.type === 'checkbox' ? fieldHtml : ''}
                <label for="aux-${key}" style="${config.type === 'checkbox' ? 'margin-bottom:0;' : ''}">${config.label} ${config.required ? '*' : ''}</label>
                ${config.type !== 'checkbox' ? fieldHtml : ''}
            </div>
        `;
    });

    document.getElementById('aux-modal-title').textContent = id ? `Editar Registro #${id}` : 'Nuevo Registro';
    document.getElementById('aux-feedback').textContent = '';
    document.getElementById('aux-modal').style.display = 'flex';
}

async function saveAuxRecord(e) {
    e.preventDefault();
    if (!currentAuxTable) return;

    const feedback = document.getElementById('aux-feedback');
    const schema = AUX_SCHEMAS[currentAuxTable];
    const payload = {};

    Object.keys(schema).forEach(key => {
        const field = document.getElementById(`aux-${key}`);
        if (schema[key].type === 'checkbox') {
            payload[key] = field.checked;
        } else {
            const val = field.value.trim();
            payload[key] = val === '' ? null : val;
        }
    });

    feedback.style.color = "var(--text-primary)";
    feedback.textContent = "Guardando...";

    try {
        const method = editingAuxId ? 'PUT' : 'POST';
        const url = editingAuxId ?
            `${API_URL}/api/v1/auxiliares/${currentAuxTable}/${editingAuxId}` :
            `${API_URL}/api/v1/auxiliares/${currentAuxTable}`;

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await res.json();
        if (res.ok) {
            document.getElementById('aux-modal').style.display = 'none';
            loadAuxTable();
        } else {
            feedback.style.color = "var(--error)";
            feedback.textContent = result.detail || "Ocurrió un error al guardar.";
        }
    } catch (error) {
        feedback.style.color = "var(--error)";
        feedback.textContent = "Error de red al conectar con el servidor.";
    }
}

// -------------------------------------------------------------
// Listado de Clientes Logic
// -------------------------------------------------------------
async function viewClientCredits(cuil) {
    switchTab('listado-creditos');
    await loadCreditosTable();

    if (!excelFilters['table-creditos']) {
        excelFilters['table-creditos'] = {};
    }

    // The "Cliente CUIL" column is at index 2
    excelFilters['table-creditos'][2] = {
        isDate: false,
        desde: '',
        hasta: '',
        allowedSet: new Set([String(cuil)])
    };

    runAllExcelFilters('table-creditos', 'creditos-headers');
}

async function viewClientCuentaCorriente(cuil) {
    const tbody = document.getElementById('cliente-cta-cte-body');
    tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">Cargando cuenta corriente...</td></tr>';

    // Configurar título del modal
    const titleEl = document.getElementById('cliente-cta-cte-title');
    let clienteName = cuil;
    if (window.clientesDataCache) {
        const cliente = window.clientesDataCache.find(c => c.CUIL === cuil);
        if (cliente) {
            clienteName = `${cliente['Apellido y Nombre']} (CUIL: ${cuil})`;
        }
    }
    titleEl.textContent = `Cuenta Corriente Unificada: ${clienteName}`;

    switchTab('cliente-cta-cte');

    try {
        const res = await fetch(`${API_URL}/api/v1/clientes/${cuil}/cuenta_corriente`);
        if (!res.ok) throw new Error("Error al obtener la cuenta corriente del cliente.");

        const data = await res.json();
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay cuotas registradas para este cliente.</td></tr>';
            document.getElementById('cliente-cta-cte-headers').innerHTML = '';
            return;
        }

        excelFilters['table-cliente-cta-cte'] = {};
        const headers = ["Crédito (ID)", "N° Cuota", "Vencimiento", "Capital", "Interés", "IVA", "Total Esperado", "Cobrado", "Saldo Pendiente", "Estado"];
        let theadHtml = "<tr>";
        headers.forEach((h, i) => {
            theadHtml += `<th><div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;"><span>${h}</span><span class="filter-icon filter-icon-table-cliente-cta-cte" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-cliente-cta-cte', 'cliente-cta-cte-headers')">▼</span></div></th>`;
        });
        theadHtml += "</tr>";
        document.getElementById('cliente-cta-cte-headers').innerHTML = theadHtml;

        let html = "";
        data.forEach(c => {
            const extStr = c.id_externo && c.id_externo !== '-' ? ` (${c.id_externo})` : '';
            const creditoLabel = `#${c.credito_id}${extStr}`;

            html += `<tr class="main-row">
                <td>${creditoLabel}</td>
                <td>${c.nro_cuota}</td>
                <td>${c.vencimiento}</td>
                <td>${formatCurrency(c.capital)}</td>
                <td>${formatCurrency(c.interes)}</td>
                <td>${formatCurrency(c.iva)}</td>
                <td style="font-weight: 600;">${formatCurrency(c.total_esperado)}</td>
                <td style="color: var(--accent-secondary); font-weight: 600;">${formatCurrency(c.total_cobrado)}</td>
                <td style="color: ${c.estado === 'MOROSA' ? 'var(--error)' :
                    c.estado === 'PENDIENTE' ? 'var(--accent-secondary)' : 'inherit'
                }; font-weight: 500;">
                    ${c.estado === 'CANCELADA' ? '-' : formatCurrency(c.saldo_pendiente)}
                </td>
                <td>
                    <span style="padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
                        background: ${c.estado === 'CANCELADA' ? 'var(--accent-secondary)' :
                    c.estado === 'MOROSA' ? 'var(--error)' :
                        'rgba(255,255,255,0.1)'
                };
                        color: #fff;
                    ">${c.estado}</span>
                </td>
            </tr>`;

            if (c.detalle_cobranzas && c.detalle_cobranzas.length > 0) {
                c.detalle_cobranzas.forEach(cob => {
                    html += `<tr class="sub-row" style="background: rgba(255, 255, 255, 0.02); font-size: 12px; color: var(--text-secondary);">
                        <td colspan="3" style="text-align: right; border-left: 2px solid var(--accent-secondary);">
                            ↳ Cobranza (${cob.tipo}) el ${cob.fecha}
                        </td>
                        <td>${formatCurrency(cob.capital)}</td>
                        <td>${formatCurrency(cob.interes)}</td>
                        <td>${formatCurrency(cob.iva)}</td>
                        <td>-</td>
                        <td style="color: var(--accent-secondary);">${formatCurrency(cob.total)}</td>
                        <td colspan="2"></td>
                    </tr>`;
                });
            }
        });

        tbody.innerHTML = html;
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center; color: var(--error);">${error.message}</td></tr>`;
    }
}

async function loadClientesTable() {
    const tbody = document.querySelector('#table-clientes tbody');
    const thead = document.getElementById('clientes-headers');

    tbody.innerHTML = '<tr><td colspan="100%" class="text-center empty-state" style="padding:40px;">Cargando clientes...</td></tr>';

    // Clear filters
    if (!excelFilters['table-clientes']) excelFilters['table-clientes'] = {};
    else excelFilters['table-clientes'] = {};

    try {
        const res = await fetch(`${API_URL}/api/v1/clientes`);
        if (!res.ok) throw new Error("Error al cargar clientes");
        const data = await res.json();

        // Cache data globally for name lookup in modals
        window.clientesDataCache = data;

        if (data.length === 0) {
            thead.innerHTML = '';
            tbody.innerHTML = '<tr><td colspan="100%" class="empty-state text-center" style="padding:40px;">No hay clientes registrados.</td></tr>';
            return;
        }

        const keys = Object.keys(data[0]);
        let theadHtml = "<tr>";
        keys.forEach((k, i) => {
            theadHtml += `<th>
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                    <span>${k}</span>
                    <span class="filter-icon filter-icon-table-clientes" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-clientes', 'clientes-headers')">▼</span>
                </div>
            </th>`;
        });
        theadHtml += `<th>Acciones</th></tr>`;
        thead.innerHTML = theadHtml;

        let tbodyHtml = "";
        data.forEach(row => {
            let rowHtml = "<tr>";
            keys.forEach(k => {
                let val = row[k];
                if (k === 'Remuneración' && val !== null && val !== undefined) {
                    val = formatCurrency(val);
                } else if (k === 'Estado' && val !== null && val !== undefined) {
                    const statusClass = `status-badge status-${String(val).toLowerCase().replace(/\\s+/g, '-')}`;
                    val = `<span class="${statusClass}">${val}</span>`;
                }
                rowHtml += `<td>${val !== null ? val : '-'}</td>`;
            });
            rowHtml += `
                <td style="white-space: nowrap;">
                    <a href="#listado-clientes?cta_cte=${row.CUIL}" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; margin-right: 4px; text-decoration: none; display: inline-block; box-sizing: border-box;" onclick="viewClientCuentaCorriente('${row.CUIL}')">👁️ Cta. Cte.</a>
                    <a href="#listado-creditos?cliente=${row.CUIL}" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; margin-right: 4px; text-decoration: none; display: inline-block; box-sizing: border-box;" onclick="viewClientCredits('${row.CUIL}')">👁️ Créditos</a>
                    <a href="#clientes?edit=${row.CUIL}" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; margin-right: 4px; text-decoration: none; display: inline-block; box-sizing: border-box;" onclick="editCliente('${row.CUIL}')">✏️ Editar</a>
                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px; color: var(--error);" onclick="deleteCliente('${row.CUIL}')">🗑️ Borrar</button>
                </td>
            </tr>`;
            tbodyHtml += rowHtml;
        });
        tbody.innerHTML = tbodyHtml;

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center; color: var(--error);">Error al cargar clientes: ${e.message}</td></tr>`;
    }
}

// -------------------------------------------------------------
// Listado de Créditos Logic
// -------------------------------------------------------------
function openStatusModal(id, currentStatus) {
    document.getElementById('status-credito-id').value = id;
    document.getElementById('status-select').value = currentStatus;
    document.getElementById('status-modal').style.display = 'flex';
}

async function saveCreditoStatus(e) {
    e.preventDefault();
    const id = document.getElementById('status-credito-id').value;
    const nuevoEstado = document.getElementById('status-select').value;

    try {
        const res = await fetch(`${API_URL}/api/v1/creditos/${id}/estado`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado: nuevoEstado })
        });

        if (res.ok) {
            document.getElementById('status-modal').style.display = 'none';
            loadCreditosTable(); // Recargar la tabla
        } else {
            const data = await res.json();
            alert(`Error al actualizar: ${data.detail}`);
        }
    } catch (error) {
        alert("Ocurrió un error de red al intentar actualizar el estado.");
    }
}

async function viewCreditoCuotas(id) {
    const tbody = document.getElementById('cuotas-body');
    tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">Cargando cuotas...</td></tr>';
    switchTab('credito-cuotas');

    try {
        const res = await fetch(`${API_URL}/api/v1/creditos/${id}/cuotas`);
        if (!res.ok) throw new Error("Error al obtener las cuotas del crédito.");

        const data = await res.json();
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay cuotas registradas para este crédito.</td></tr>';
            document.getElementById('cuotas-headers').innerHTML = '';
            return;
        }

        excelFilters['table-cuotas'] = {};
        const headers = ["N°", "Vencimiento", "Capital", "Interés", "IVA", "Total Esperado", "Cobrado", "Saldo Pendiente", "Estado"];
        let theadHtml = "<tr>";
        headers.forEach((h, i) => {
            theadHtml += `<th><div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;"><span>${h}</span><span class="filter-icon filter-icon-table-cuotas" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-cuotas', 'cuotas-headers')">▼</span></div></th>`;
        });
        theadHtml += "</tr>";
        document.getElementById('cuotas-headers').innerHTML = theadHtml;

        let html = "";
        data.forEach(c => {
            html += `<tr class="main-row">
                <td>${c.nro_cuota}</td>
                <td>${c.vencimiento}</td>
                <td>${formatCurrency(c.capital)}</td>
                <td>${formatCurrency(c.interes)}</td>
                <td>${formatCurrency(c.iva)}</td>
                <td style="font-weight: 600;">${formatCurrency(c.total_esperado)}</td>
                <td style="color: var(--accent-secondary); font-weight: 600;">${formatCurrency(c.total_cobrado)}</td>
                <td style="color: ${c.estado === 'MOROSA' ? 'var(--error)' :
                    c.estado === 'PENDIENTE' ? 'var(--accent-secondary)' : 'inherit'
                }; font-weight: 500;">
                    ${c.estado === 'CANCELADA' ? '-' : formatCurrency(c.saldo_pendiente)}
                </td>
                <td>
                    <span style="padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
                        background: ${c.estado === 'CANCELADA' ? 'var(--accent-secondary)' :
                    c.estado === 'MOROSA' ? 'var(--error)' :
                        'rgba(255,255,255,0.1)'
                };
                        color: ${c.estado === 'PENDIENTE' ? '#fff' : '#fff'};
                    ">${c.estado}</span>
                </td>
            </tr>`;

            if (c.detalle_cobranzas && c.detalle_cobranzas.length > 0) {
                c.detalle_cobranzas.forEach(cob => {
                    html += `<tr class="sub-row" style="background: rgba(255, 255, 255, 0.02); font-size: 12px; color: var(--text-secondary);">
                        <td colspan="2" style="text-align: right; border-left: 2px solid var(--accent-secondary);">
                            ↳ Cobranza (${cob.tipo}) el ${cob.fecha}
                        </td>
                        <td>${formatCurrency(cob.capital)}</td>
                        <td>${formatCurrency(cob.interes)}</td>
                        <td>${formatCurrency(cob.iva)}</td>
                        <td>-</td>
                        <td style="color: var(--accent-secondary);">${formatCurrency(cob.total)}</td>
                        <td colspan="2"></td>
                    </tr>`;
                });
            }
        });

        tbody.innerHTML = html;
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center; color: var(--error);">${error.message}</td></tr>`;
    }
}

async function loadCreditosTable() {
    const tbody = document.getElementById('creditos-body');
    const thead = document.getElementById('creditos-headers');

    tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">Cargando créditos...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/api/v1/creditos`);
        if (!res.ok) throw new Error("Error al obtener los créditos del servidor");
        const data = await res.json();

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay créditos registrados.</td></tr>';
            thead.innerHTML = '';
            return;
        }

        // Configure table filtering data
        window.tableDataCache = window.tableDataCache || {};
        window.tableDataCache['table-creditos'] = data;

        const keys = Object.keys(data[0]);
        let theadHtml = "<tr>";
        keys.forEach((k, i) => {
            theadHtml += `<th>
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                    <span>${k}</span>
                    <span class="filter-icon filter-icon-table-creditos" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-creditos', 'creditos-headers')">▼</span>
                </div>
            </th>`;
        });
        theadHtml += "<th>Acciones</th></tr>";
        thead.innerHTML = theadHtml;

        let tbodyHtml = "";
        data.forEach(row => {
            let rowHtml = "<tr>";
            keys.forEach(k => {
                let val = row[k];
                if (k === 'Capital' && val !== null && val !== undefined) {
                    val = formatCurrency(val);
                } else if (k === 'TNA con IVA' && val !== null && val !== undefined) {
                    val = `${(val * 100).toFixed(2)}%`;
                } else if (k === 'Estado' && val !== null && val !== undefined) {
                    const statusClass = `status-badge status-${String(val).toLowerCase().replace(/\s+/g, '-')}`;
                    val = `<span class="${statusClass}">${val}</span>`;
                }
                rowHtml += `<td>${val !== null ? val : '-'}</td>`;
            });
            rowHtml += `
                <td style="white-space: nowrap;">
                    <div style="display: flex; gap: 4px;">
                        <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="openStatusModal('${row.ID}', '${row.Estado}')">✏️ Estado</button>
                        <a href="#listado-creditos?credito_cta=${row.ID}" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; text-decoration: none; display: inline-block; box-sizing: border-box;" onclick="viewCreditoCuotas('${row.ID}')">👁️ Cuenta</a>
                        <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px; color: var(--error); border-color: var(--error);" onclick="deleteCredito('${row.ID}')">🗑️ Borrar</button>
                    </div>
                </td>
            </tr>`;
            tbodyHtml += rowHtml;
        });
        tbody.innerHTML = tbodyHtml;

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center; color: var(--error);">Error al cargar créditos: ${e.message}</td></tr>`;
    }
}

async function deleteCredito(creditoId) {
    if (!confirm("¿Está seguro que desea eliminar este crédito? Esta acción no se puede deshacer y solo es posible si no tiene cobranzas asociadas.")) {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/api/v1/creditos/${creditoId}`, {
            method: 'DELETE'
        });

        const data = await res.json();

        if (res.ok) {
            alert("✅ " + data.message);
            loadCreditosTable(); // Recargar la tabla
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (error) {
        alert(`Ocurrió un error de red al intentar eliminar el crédito: ${error.message}`);
    }
}

// -------------------------------------------------------------
// Cobranzas Logic
// -------------------------------------------------------------
async function loadCobranzasTable() {
    const tbody = document.getElementById('cobranzas-body');
    const thead = document.getElementById('cobranzas-headers');

    tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center;">Cargando cobranzas...</td></tr>`;

    if (!excelFilters['table-cobranzas']) excelFilters['table-cobranzas'] = {};
    else excelFilters['table-cobranzas'] = {};

    try {
        const res = await fetch(`${API_URL}/api/v1/cobranzas`);
        if (!res.ok) throw new Error("Error fetching data");

        const data = await res.json();

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay cobranzas registradas.</td></tr>';
            thead.innerHTML = '';
            return;
        }

        window.tableDataCache = window.tableDataCache || {};
        window.tableDataCache['table-cobranzas'] = data;

        const keys = Object.keys(data[0]);
        let theadHtml = "<tr>";
        keys.forEach((k, i) => {
            theadHtml += `<th>
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                    <span>${k}</span>
                    <span class="filter-icon filter-icon-table-cobranzas" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-cobranzas', 'cobranzas-headers')">▼</span>
                </div>
            </th>`;
        });
        theadHtml += "<th>Acciones</th></tr>";
        thead.innerHTML = theadHtml;

        let tbodyHtml = "";
        data.forEach(row => {
            let rowHtml = "<tr>";
            keys.forEach(k => {
                let val = row[k];
                if (['Total', 'Capital', 'Interés', 'IVA'].includes(k) && val !== null && val !== undefined) {
                    val = formatCurrency(val);
                    const weight = k === 'Total' ? '600' : 'normal';
                    rowHtml += `<td style="font-weight: ${weight};">${val}</td>`;
                } else if (k === 'Tipo' && val !== null && val !== undefined) {
                    const statusClass = `status-badge status-${String(val).toLowerCase().replace(/\s+/g, '-')}`;
                    rowHtml += `<td><span class="${statusClass}">${val}</span></td>`;
                } else {
                    rowHtml += `<td>${val !== null ? val : '-'}</td>`;
                }
            });
            rowHtml += `
                <td style="white-space: nowrap;">
                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px; color: var(--error); border-color: var(--error);" onclick="deleteCobranza('${row.ID}')">🗑️ Borrar</button>
                </td>
            </tr>`;
            tbodyHtml += rowHtml;
        });
        tbody.innerHTML = tbodyHtml;

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align:left; color: var(--error);"><pre>Error: ${e.message}\n${e.stack}</pre></td></tr>`;
        console.error("loadCobranzasTable failed:", e);
    }
}

window.deleteCobranza = async function(cobranzaId) {
    if (!confirm("¿Está seguro que desea eliminar esta cobranza individual? Esta acción no se puede deshacer y ajustará el estado de la cuota correspondiente.")) {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/api/v1/cobranzas/${cobranzaId}`, {
            method: 'DELETE'
        });

        const data = await res.json();

        if (res.ok) {
            alert("✅ " + data.message);
            loadCobranzasTable(); // Recargar la tabla
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (error) {
        alert(`Ocurrió un error de red al intentar eliminar la cobranza: ${error.message}`);
    }
};

// -------------------------------------------------------------
// Procesos Logic
// -------------------------------------------------------------
async function loadProcesosTable() {
    const tbody = document.getElementById('procesos-body');
    const thead = document.getElementById('procesos-headers');

    tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center;">Cargando procesos...</td></tr>`;

    if (!excelFilters['table-procesos']) excelFilters['table-procesos'] = {};
    else excelFilters['table-procesos'] = {};

    try {
        const res = await fetch(`${API_URL}/api/v1/procesos`);
        if (!res.ok) throw new Error("Error fetching procesos");

        const data = await res.json();

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay procesos registrados.</td></tr>';
            thead.innerHTML = '';
            return;
        }

        window.tableDataCache = window.tableDataCache || {};
        window.tableDataCache['table-procesos'] = data;

        const keys = Object.keys(data[0]);
        let theadHtml = "<tr>";
        keys.forEach((k, i) => {
            theadHtml += `<th>
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                    <span>${k}</span>
                    <span class="filter-icon filter-icon-table-procesos" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-procesos', 'procesos-headers')">▼</span>
                </div>
            </th>`;
        });
        theadHtml += "<th>Acciones</th></tr>";
        thead.innerHTML = theadHtml;

        let tbodyHtml = "";
        data.forEach(row => {
            let rowHtml = "<tr>";
            keys.forEach(k => {
                let val = row[k];
                if ((k === 'Estado' || k === 'Tipo') && val !== null && val !== undefined) {
                    const statusClass = `status-badge status-${String(val).toLowerCase().replace(/\s+/g, '-')}`;
                    rowHtml += `<td><span class="${statusClass}">${val}</span></td>`;
                } else {
                    rowHtml += `<td>${val !== null ? val : '-'}</td>`;
                }
            });
            rowHtml += `
                <td style="white-space: nowrap;">
                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px; margin-right: 8px;" onclick="viewCobranzasProceso('${row.ID}')">🔍 Ver Cobranzas</button>
                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px; color: var(--error); border-color: var(--error);" onclick="deleteProceso('${row.ID}')">🗑️ Borrar</button>
                </td>
            </tr>`;
            tbodyHtml += rowHtml;
        });
        tbody.innerHTML = tbodyHtml;

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align:left; color: var(--error);"><pre>Error: ${e.message}\n${e.stack}</pre></td></tr>`;
        console.error("loadProcesosTable failed:", e);
    }
}

async function deleteProceso(procesoId) {
    if (!confirm("¿Está seguro que desea eliminar este proceso de ingesta y todas sus cobranzas asociadas?")) {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/api/v1/procesos/${procesoId}`, {
            method: 'DELETE'
        });

        const data = await res.json();

        if (res.ok) {
            alert("✅ " + data.message);
            loadProcesosTable();
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (error) {
        alert(`Ocurrió un error de red al intentar eliminar el proceso: ${error.message}`);
    }
}

window.viewCobranzasProceso = async function (procesoId) {
    // Navigate to Cobranzas tab
    switchTab('listado-cobranzas');

    // Ensure the table is loaded
    await loadCobranzasTable();

    // In the new API layout, Proceso ID is the 2nd column (index 1)
    const tableId = 'table-cobranzas';
    const headerId = 'cobranzas-headers';
    const colIndex = 1;

    if (!excelFilters[tableId]) excelFilters[tableId] = {};
    excelFilters[tableId][colIndex] = {
        isDate: false,
        desde: '',
        hasta: '',
        allowedSet: new Set([String(procesoId)])
    };

    runAllExcelFilters(tableId, headerId);
}

// -------------------------------------------------------------
// System Actions Logic
// -------------------------------------------------------------
async function syncSystemStates() {
    const btn = document.getElementById('btn-sync-states');
    btn.disabled = true;
    btn.innerText = "Sincronizando...";

    try {
        const res = await fetch(`${API_URL}/api/v1/system/sync-states`, {
            method: 'POST'
        });
        const data = await res.json();

        if (res.ok) {
            alert("¡Éxito! " + data.message);
        } else {
            alert(`Error durante la sincronización: ${data.detail}`);
        }
    } catch (error) {
        alert("Ocurrió un error de red al intentar sincronizar.");
    } finally {
        btn.disabled = false;
        btn.innerText = "Ejecutar Sincronización";

        // Refresh tables if their tabs are active or data is cached
        if (document.getElementById('tab-clientes').classList.contains('active')) {
            loadClientesTable();
        } else if (document.getElementById('tab-listado-creditos').classList.contains('active')) {
            loadCreditosTable();
        }
    }
}

// -------------------------------------------------------------
// Alta de Crédito Logic
// -------------------------------------------------------------
async function searchClienteForCredito() {
    const query = document.getElementById('search-cli-input').value.trim();
    const resultDiv = document.getElementById('search-cli-result');
    const updateContainer = document.getElementById('alta-credito-cliente-container');
    const formContainer = document.getElementById('alta-credito-form-container');

    if (!query) {
        resultDiv.style.display = 'block';
        resultDiv.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
        resultDiv.style.border = '1px solid var(--error)';
        resultDiv.innerHTML = '<p style="color: var(--error);">Por favor ingrese un CUIL o DNI.</p>';
        return;
    }

    updateContainer.style.display = 'none';
    formContainer.style.display = 'none';

    try {
        const resList = await fetch(`${API_URL}/api/v1/clientes`);
        const data = await resList.json();
        const found = data.find(c => c.CUIL === query || c.Documento === query);

        if (found) {
            // Fetch full details to populate update form
            const fullRes = await fetch(`${API_URL}/api/v1/clientes/${found.CUIL}`);
            if (!fullRes.ok) throw new Error("No se pudieron cargar los detalles del cliente.");
            const cliente = await fullRes.json();

            resultDiv.style.display = 'block';
            resultDiv.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
            resultDiv.style.border = '1px solid var(--accent-secondary)';
            resultDiv.innerHTML = `<p style="color: var(--accent-secondary); margin: 0;">✅ Cliente encontrado: <strong>${cliente.apellido}, ${cliente.nombre}</strong></p>`;

            // Populate Update Form
            const setVal = (id, val) => document.getElementById(id).value = val || '';
            setVal('upd-cli-cuil', cliente.cuil);
            setVal('upd-cli-documento', cliente.documento);
            setVal('upd-cli-nombre', cliente.nombre);
            setVal('upd-cli-apellido', cliente.apellido);

            // Format dates for input[type="date"]
            if (cliente.fecha_nacimiento) {
                setVal('upd-cli-nacimiento', cliente.fecha_nacimiento);
            } else {
                setVal('upd-cli-nacimiento', '');
            }

            setVal('upd-cli-sexo', cliente.sexo);
            setVal('upd-cli-estcivil', cliente.estado_civil);
            setVal('upd-cli-nacionalidad', cliente.nacionalidad);
            setVal('upd-cli-telefono', cliente.telefono);
            setVal('upd-cli-telefono2', cliente.telefono_2);
            setVal('upd-cli-mail', cliente.mail);
            setVal('upd-cli-calle', cliente.calle);
            setVal('upd-cli-callenro', cliente.calle_nro);
            setVal('upd-cli-piso', cliente.piso);
            setVal('upd-cli-depto', cliente.depto);
            setVal('upd-cli-localidad', cliente.localidad);
            setVal('upd-cli-cp', cliente.id_codigo_postal);
            setVal('upd-cli-provincia', cliente.id_provincia);
            setVal('upd-cli-remuneracion', cliente.remuneracion);
            setVal('upd-cli-legajo', cliente.legajo);
            setVal('upd-cli-empleador', cliente.empleador_id);

            // Reset button if it was confirmed before
            const btn = document.getElementById('btn-confirmar-cliente');
            btn.disabled = false;
            btn.innerText = "Confirmar y Actualizar Datos";
            btn.style.backgroundColor = "var(--accent-primary)";

            updateContainer.style.display = 'block';
        } else {
            resultDiv.style.display = 'block';
            resultDiv.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
            resultDiv.style.border = '1px solid var(--error)';
            resultDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <p style="color: var(--error); margin: 0;">❌ Cliente no encontrado.</p>
                    <button class="btn-primary" onclick="switchTab('clientes')" style="font-size: 13px; padding: 6px 12px; height: auto;">Ir a Alta de Cliente</button>
                </div>
            `;
        }
    } catch (error) {
        resultDiv.style.display = 'block';
        resultDiv.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
        resultDiv.innerHTML = `<p style="color: var(--error); margin: 0;">Error en la búsqueda: ${error.message}</p>`;
    }
}

async function confirmUpdateClienteForCredito(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-confirmar-cliente');
    btn.disabled = true;
    btn.innerText = "Actualizando...";

    const cuil = document.getElementById('upd-cli-cuil').value;

    // Helper to get value or null
    const getVal = (id) => document.getElementById(id).value.trim() || null;
    const getNum = (id) => {
        const val = document.getElementById(id).value;
        return val ? parseInt(val, 10) : null;
    };

    const payload = {
        cuil: cuil,
        documento: document.getElementById('upd-cli-documento').value,
        nombre: document.getElementById('upd-cli-nombre').value,
        apellido: document.getElementById('upd-cli-apellido').value,
        fecha_nacimiento: getVal('upd-cli-nacimiento'),
        sexo: getVal('upd-cli-sexo'),
        estado_civil: getVal('upd-cli-estcivil'),
        nacionalidad: getVal('upd-cli-nacionalidad'),
        telefono: getVal('upd-cli-telefono'),
        telefono_2: getVal('upd-cli-telefono2'),
        mail: getVal('upd-cli-mail'),
        calle: getVal('upd-cli-calle'),
        calle_nro: getNum('upd-cli-callenro'),
        piso: getVal('upd-cli-piso'),
        depto: getVal('upd-cli-depto'),
        localidad: getVal('upd-cli-localidad'),
        id_codigo_postal: getVal('upd-cli-cp'),
        id_provincia: getNum('upd-cli-provincia'),
        remuneracion: parseFloat(document.getElementById('upd-cli-remuneracion').value || 0),
        legajo: getVal('upd-cli-legajo'),
        empleador_id: getNum('upd-cli-empleador')
    };

    try {
        const res = await fetch(`${API_URL}/api/v1/clientes/${cuil}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            btn.innerText = "¡Datos Confirmados!";
            btn.style.backgroundColor = "var(--accent-secondary)";
            // Show credit form
            document.getElementById('alta-credito-form-container').style.display = 'block';
            setupCreditFormForEmpleador(payload.empleador_id);
        } else {
            alert(`Error al actualizar cliente: ${data.detail}`);
            btn.innerText = "Confirmar y Actualizar Datos";
            btn.disabled = false;
        }
    } catch (err) {
        alert("Ocurrió un error de red al intentar actualizar el cliente.");
        btn.innerText = "Confirmar y Actualizar Datos";
        btn.disabled = false;
    }
}

function setTasasMode(auto) {
    const autoContainer = document.getElementById('container-tasa-auto');
    const manualPlazo = document.getElementById('container-tasa-manual-plazo');
    const manualTna = document.getElementById('container-tasa-manual-tna');
    const selectTasas = document.getElementById('cred-tasa-seleccion');
    const inputPlazo = document.getElementById('cred-plazo');
    const inputTna = document.getElementById('cred-tna');

    if (auto) {
        autoContainer.style.display = 'block';
        manualPlazo.style.display = 'none';
        manualTna.style.display = 'none';
        selectTasas.required = true;

        inputPlazo.required = false;
        inputTna.required = false;
        inputPlazo.type = "hidden";
        inputTna.type = "hidden";
    } else {
        autoContainer.style.display = 'none';
        manualPlazo.style.display = 'block';
        manualTna.style.display = 'block';
        selectTasas.required = false;

        inputPlazo.required = true;
        inputTna.required = true;
        inputPlazo.type = "number";
        inputTna.type = "number";
        inputPlazo.value = "";
        inputTna.value = "";
    }
}

function setupCreditFormForEmpleador(empleadorId) {
    const selectSocio = document.getElementById('cred-socio');
    if (!empleadorId) {
        selectSocio.value = '';
        selectSocio.disabled = false;
        setTasasMode(false);
        return;
    }

    if (window.empleadoresDataCache) {
        const emp = window.empleadoresDataCache.find(e => e.id === empleadorId);
        if (emp && emp.socio_comercial_id) {
            selectSocio.value = emp.socio_comercial_id;
            selectSocio.disabled = true; // Lock it
            updateTasasDropdown();
        } else {
            selectSocio.value = '';
            selectSocio.disabled = false;
            setTasasMode(false);
        }
    } else {
        setTasasMode(false);
    }
}

function updateTasasDropdown() {
    const socioId = parseInt(document.getElementById('cred-socio').value, 10);
    let emisionDateStr = document.getElementById('cred-emision').value;
    if (!emisionDateStr) {
        // use today
        const today = new Date();
        emisionDateStr = today.toISOString().split('T')[0];
    }
    const targetDate = new Date(emisionDateStr + 'T00:00:00');

    const selectTasas = document.getElementById('cred-tasa-seleccion');
    if (!selectTasas) return;

    selectTasas.innerHTML = '<option value="">Seleccione una opción...</option>';
    document.getElementById('cred-plazo').value = '';
    document.getElementById('cred-tna').value = '';

    if (!socioId || !window.tasasDataCache) {
        setTasasMode(false);
        return;
    }

    // Filter by socio, ACTIVA, and fecha <= emision
    const validTasas = window.tasasDataCache.filter(t => {
        if (t.socio_originador_id !== socioId) return false;
        if (t.estado !== 'ACTIVA') return false;
        if (t.fecha) {
            const tasaDate = new Date(t.fecha + 'T00:00:00');
            if (tasaDate > targetDate) return false;
        }
        return true;
    });

    if (validTasas.length === 0) {
        setTasasMode(false);
        return;
    }

    setTasasMode(true);

    // Group by plazo and get max fecha
    const grouped = {};
    validTasas.forEach(t => {
        if (!grouped[t.plazo] || (new Date(t.fecha + 'T00:00:00') > new Date(grouped[t.plazo].fecha + 'T00:00:00'))) {
            grouped[t.plazo] = t;
        }
    });

    // Populate dropdown
    Object.values(grouped).sort((a, b) => a.plazo - b.plazo).forEach(t => {
        const option = document.createElement('option');
        // value is JSON with plazo, tna and comision_id (tna must be a decimal, so we divide the % by 100)
        option.value = JSON.stringify({ plazo: t.plazo, tna: t.tna_c_iva / 100, comision_id: t.id });
        const tnaPct = Number(t.tna_c_iva).toFixed(2);
        option.innerText = `${t.plazo} cuotas - TNA ${tnaPct}%`;
        selectTasas.appendChild(option);
    });
}

function updateHiddenTasas() {
    const select = document.getElementById('cred-tasa-seleccion');
    const val = select.value;
    if (val) {
        const data = JSON.parse(val);
        document.getElementById('cred-plazo').value = data.plazo;
        document.getElementById('cred-tna').value = data.tna;
    } else {
        document.getElementById('cred-plazo').value = '';
        document.getElementById('cred-tna').value = '';
    }
}

async function submitAltaCredito(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerText = "Procesando...";

    let comisionId = null;
    const isAutoMode = document.getElementById('container-tasa-auto') && document.getElementById('container-tasa-auto').style.display !== 'none';
    const tasaSelect = document.getElementById('cred-tasa-seleccion');
    if (isAutoMode && tasaSelect && tasaSelect.value) {
        try {
            const data = JSON.parse(tasaSelect.value);
            comisionId = data.comision_id || null;
        } catch (e) { }
    }

    const payload = {
        cliente_cuil: document.getElementById('upd-cli-cuil').value,
        capital: parseFloat(document.getElementById('cred-capital').value),
        tna_c_iva: parseFloat(document.getElementById('cred-tna').value),
        plazo: parseInt(document.getElementById('cred-plazo').value, 10),
        tipo_credito: document.getElementById('cred-tipo').value,
        socio_originador_id: document.getElementById('cred-socio').value ? parseInt(document.getElementById('cred-socio').value, 10) : null,
        comision_id: comisionId,
        fecha_emision: document.getElementById('cred-emision').value || null
    };

    try {
        const res = await fetch(`${API_URL}/api/v1/creditos/originacion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            alert("¡Crédito generado exitosamente!");
            // Limpiar formularios
            e.target.reset();
            document.getElementById('form-update-cliente-credito').reset();
            document.getElementById('alta-credito-cliente-container').style.display = 'none';
            document.getElementById('alta-credito-form-container').style.display = 'none';
            document.getElementById('search-cli-result').style.display = 'none';
            document.getElementById('search-cli-input').value = '';

            // Recargar tabla de créditos
            loadCreditosTable();

            // Abrir el modal de cuenta corriente para este nuevo crédito
            if (data.credito_id) {
                viewCreditoCuotas(data.credito_id);
            }
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (err) {
        alert("Ocurrió un error de red al intentar generar el crédito.");
    } finally {
        btn.disabled = false;
        btn.innerText = "Originación de Crédito";
    }
}

// -------------------------------------------------------------
// Procesamiento de Cobranzas Logic
// -------------------------------------------------------------
window.submitCobranzaIndividual = async function(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    const feedback = document.getElementById('cob-ind-feedback');
    btn.disabled = true;
    btn.innerText = "Procesando...";
    feedback.innerText = "";
    feedback.style.color = "inherit";

    const payload = {
        identificador: document.getElementById('cob-ind-identificador').value,
        id_val: document.getElementById('cob-ind-valor').value,
        monto: parseFloat(document.getElementById('cob-ind-monto').value),
        fecha_pago: document.getElementById('cob-ind-fecha').value || null,
        anticipada: document.getElementById('cob-ind-tipo').value === 'anticipada'
    };

    try {
        const res = await fetch(`${API_URL}/api/v1/cobranzas/individual`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            feedback.innerText = "✅ " + data.message;
            feedback.style.color = "var(--accent-secondary)";
            e.target.reset();
            // Refrescar tablas en background
            loadCobranzasTable();
            loadProcesosTable();
        } else {
            feedback.innerText = `❌ Error: ${data.detail}`;
            feedback.style.color = "var(--error)";
        }
    } catch (err) {
        feedback.innerText = `❌ Error de red: ${err.message}`;
        feedback.style.color = "var(--error)";
    } finally {
        btn.disabled = false;
        btn.innerText = "Procesar Cobranza Individual";
    }
};

window.submitCobranzaMasiva = async function(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    const feedback = document.getElementById('cob-mas-feedback');
    btn.disabled = true;
    btn.innerText = "Subiendo y Procesando...";
    feedback.innerText = "";
    feedback.style.color = "inherit";

    const formData = new FormData();
    formData.append('identificador', document.getElementById('cob-mas-identificador').value);
    formData.append('id_column', document.getElementById('cob-mas-col-id').value);
    formData.append('amount_column', document.getElementById('cob-mas-col-monto').value);
    
    const fecha = document.getElementById('cob-mas-fecha').value;
    if (fecha) {
        formData.append('fecha_pago', fecha);
    }
    
    formData.append('anticipada', document.getElementById('cob-mas-tipo').value === 'anticipada');
    
    const fileInput = document.getElementById('cob-mas-file');
    if (fileInput.files.length > 0) {
        formData.append('file', fileInput.files[0]);
    }

    try {
        const res = await fetch(`${API_URL}/api/v1/cobranzas/masiva`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        if (res.ok) {
            feedback.innerText = "✅ " + data.message;
            feedback.style.color = "var(--accent-secondary)";
            e.target.reset();
            // Refrescar tablas en background
            loadCobranzasTable();
            loadProcesosTable();
        } else {
            feedback.innerText = `❌ Error: ${data.detail}`;
            feedback.style.color = "var(--error)";
        }
    } catch (err) {
        feedback.innerText = `❌ Error de red: ${err.message}`;
        feedback.style.color = "var(--error)";
    } finally {
        btn.disabled = false;
        btn.innerText = "Procesar Lote Masivo";
    }
};
