const API_URL = "http://127.0.0.1:8000";

// --- UI Navigation ---
function switchTab(tabId) {
    // Update nav buttons
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active');
    });
    event.currentTarget.classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById(`tab-${tabId}`).classList.add('active');
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
                <span class="filter-icon" data-col="${i}" onclick="openExcelFilter(event, ${i})">▼</span>
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
                cutoff.setHours(0,0,0,0);
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
                cutoff.setHours(0,0,0,0);
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
let excelFilters = {};

function getUniqueValuesForCol(colIndex) {
    const tbody = document.querySelector("#table-bal tbody");
    const trs = tbody.getElementsByTagName("tr");
    const vals = new Set();
    for (let i = 0; i < trs.length; i++) {
        const td = trs[i].getElementsByTagName("td")[colIndex];
        if (td) vals.add(td.textContent.trim());
    }
    return Array.from(vals).sort();
}

function openExcelFilter(e, colIndex) {
    e.stopPropagation();
    closeExcelFilter();

    const uniqueValues = getUniqueValuesForCol(colIndex);
    const currentlySelected = excelFilters[colIndex] || new Set(uniqueValues);

    const popover = document.createElement("div");
    popover.id = "excel-filter-popover";
    popover.className = "filter-popover glass-panel fade-in";
    
    let html = `
        <div style="margin-bottom: 8px;">
            <input type="text" id="excel-filter-search" placeholder="🔍 Buscar..." 
                style="width: 100%; padding: 6px; font-size: 12px; background: rgba(0,0,0,0.5); border: 1px solid var(--border-color); color: white; border-radius: 4px;">
        </div>
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
            <button class="btn-primary" style="font-size: 12px; padding: 6px 12px; flex-grow: 1;" onclick="applyExcelFilter(${colIndex})">Aceptar</button>
            <button class="btn-secondary" style="font-size: 12px; padding: 6px 12px;" onclick="closeExcelFilter()">Cancelar</button>
        </div>
    `;

    popover.innerHTML = html;
    document.body.appendChild(popover);

    // Posicionamiento
    const rect = e.target.getBoundingClientRect();
    popover.style.left = `${rect.left}px`;
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
            if(cb.closest('label').style.display !== 'none') {
                cb.checked = checked;
            }
        });
    });
}

function closeExcelFilter() {
    const popover = document.getElementById("excel-filter-popover");
    if (popover) popover.remove();
}

function applyExcelFilter(colIndex) {
    const selected = new Set();
    document.querySelectorAll(".excel-val-cb:checked").forEach(cb => {
        selected.add(cb.value);
    });

    const totalCheckboxes = document.querySelectorAll(".excel-val-cb").length;
    if (selected.size === totalCheckboxes) {
        delete excelFilters[colIndex];
    } else {
        excelFilters[colIndex] = selected;
    }

    closeExcelFilter();
    runAllExcelFilters();
}

function runAllExcelFilters() {
    const tbody = document.querySelector("#table-bal tbody");
    if (!tbody) return;
    const trs = tbody.getElementsByTagName("tr");

    for (let i = 0; i < trs.length; i++) {
        let rowMatch = true;
        const tds = trs[i].getElementsByTagName("td");
        
        for (const [colIndexStr, allowedSet] of Object.entries(excelFilters)) {
            const colIndex = parseInt(colIndexStr);
            if (tds[colIndex]) {
                const txtValue = tds[colIndex].textContent.trim();
                if (!allowedSet.has(txtValue)) {
                    rowMatch = false;
                    break;
                }
            }
        }
        trs[i].style.display = rowMatch ? "" : "none";
    }

    document.querySelectorAll(".filter-icon").forEach(icon => {
        const col = icon.getAttribute("data-col");
        if (excelFilters[col]) {
            icon.classList.add("active");
        } else {
            icon.classList.remove("active");
        }
    });
}

// Cerrar clickeando afuera
document.addEventListener("click", (e) => {
    if (!e.target.closest(".filter-popover") && !e.target.closest(".filter-icon")) {
        closeExcelFilter();
    }
});

// Init
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('fecha').valueAsDate = new Date();
    document.getElementById('bal-fecha').valueAsDate = new Date();
});
