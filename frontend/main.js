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
let excelFilters = {
    'table-bal': {},
    'table-clientes': {}
};

function getUniqueValuesForCol(tableId, colIndex) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    const trs = tbody.getElementsByTagName("tr");
    const vals = new Set();
    for (let i = 0; i < trs.length; i++) {
        const td = trs[i].getElementsByTagName("td")[colIndex];
        if (td) vals.add(td.textContent.trim());
    }
    return Array.from(vals).sort();
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
    
    let html = `
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

    for (let i = 0; i < trs.length; i++) {
        let rowMatch = true;
        const tds = trs[i].getElementsByTagName("td");
        
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
        trs[i].style.display = rowMatch ? "" : "none";
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

// Init
document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('fecha').valueAsDate = new Date();
    document.getElementById('bal-fecha').valueAsDate = new Date();
    
    try {
        const resProv = await fetch(`${API_URL}/api/v1/auxiliares/provincias`);
        if (resProv.ok) {
            const provincias = await resProv.json();
            const selectProv = document.getElementById('cli-provincia');
            provincias.forEach(p => {
                selectProv.innerHTML += `<option value="${p.id}">${p.nombre}</option>`;
            });
        }
        
        const resEmp = await fetch(`${API_URL}/api/v1/auxiliares/empleadores`);
        if (resEmp.ok) {
            const empleadores = await resEmp.json();
            const selectEmp = document.getElementById('cli-empleador');
            empleadores.forEach(e => {
                selectEmp.innerHTML += `<option value="${e.id}">${e.razon_social} ${e.cuit ? `(CUIT: ${e.cuit})` : ''}</option>`;
            });
        }
    } catch (e) {
        console.error("Error cargando listas desplegables:", e);
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
        if(!el) return null;
        const val = el.value.trim();
        return val === "" ? null : val;
    };
    
    const getNum = (id) => {
        const el = document.getElementById(id);
        if(!el) return null;
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
            if(el) el.value = val !== null && val !== undefined ? val : "";
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
        razon_social: { type: 'text', label: 'Razón Social', required: true }
    },
    socios: {
        razon_social: { type: 'text', label: 'Razón Social', required: true },
        cuit: { type: 'text', label: 'CUIT (Sin guiones)', required: true },
        domicilio_legal: { type: 'text', label: 'Domicilio Legal' },
        contacto_nombre: { type: 'text', label: 'Nombre de Contacto' },
        mail: { type: 'email', label: 'Email' },
        telefono: { type: 'text', label: 'Teléfono' },
        dia_corte: { type: 'number', label: 'Día de Corte', default: 28 }
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
        
        const keys = Object.keys(data[0]);
        thead.innerHTML = `<tr>${keys.map(k => `<th>${k.replace(/_/g, ' ').toUpperCase()}</th>`).join('')}<th>ACCIONES</th></tr>`;
        
        tbody.innerHTML = data.map(row => {
            return `<tr>
                ${keys.map(k => `<td>${row[k] !== null ? row[k] : '-'}</td>`).join('')}
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
        
        fieldsContainer.innerHTML += `
            <div class="form-group" style="margin-bottom:0;">
                <label for="aux-${key}">${config.label} ${config.required ? '*' : ''}</label>
                <input type="${config.type}" id="aux-${key}" value="${value}" ${requiredAttr}>
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
        const val = document.getElementById(`aux-${key}`).value.trim();
        payload[key] = val === '' ? null : val;
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
                }
                rowHtml += `<td>${val !== null ? val : '-'}</td>`;
            });
            rowHtml += `
                <td style="white-space: nowrap;">
                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px; margin-right: 4px;" onclick="viewClientCredits('${row.CUIL}')">👁️ Créditos</button>
                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px; margin-right: 4px;" onclick="editCliente('${row.CUIL}')">✏️ Editar</button>
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
    document.getElementById('cuotas-modal').style.display = 'flex';
    
    try {
        const res = await fetch(`${API_URL}/api/v1/creditos/${id}/cuotas`);
        if (!res.ok) throw new Error("Error al obtener las cuotas del crédito.");
        
        const data = await res.json();
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay cuotas registradas para este crédito.</td></tr>';
            return;
        }
        
        let html = "";
        data.forEach(c => {
            html += `<tr>
                <td>${c.nro_cuota}</td>
                <td>${c.vencimiento}</td>
                <td>${formatCurrency(c.capital)}</td>
                <td>${formatCurrency(c.interes)}</td>
                <td>${formatCurrency(c.iva)}</td>
                <td style="font-weight: 600;">${formatCurrency(c.total_esperado)}</td>
                <td style="color: var(--accent-secondary); font-weight: 600;">${formatCurrency(c.total_cobrado)}</td>
                <td style="color: ${
                    c.estado === 'MOROSA' ? 'var(--error)' :
                    c.estado === 'PENDIENTE' ? 'var(--accent-secondary)' : 'inherit'
                }; font-weight: 500;">
                    ${c.estado === 'CANCELADA' ? '-' : formatCurrency(c.saldo_pendiente)}
                </td>
                <td>
                    <span style="padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
                        background: ${
                            c.estado === 'CANCELADA' ? 'var(--accent-secondary)' : 
                            c.estado === 'MOROSA' ? 'var(--error)' : 
                            'rgba(255,255,255,0.1)'
                        };
                        color: ${c.estado === 'PENDIENTE' ? '#fff' : '#fff'};
                    ">${c.estado}</span>
                </td>
            </tr>`;
            
            if (c.detalle_cobranzas && c.detalle_cobranzas.length > 0) {
                c.detalle_cobranzas.forEach(cob => {
                    html += `<tr style="background: rgba(255, 255, 255, 0.02); font-size: 12px; color: var(--text-secondary);">
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
                }
                rowHtml += `<td>${val !== null ? val : '-'}</td>`;
            });
            rowHtml += `
                <td style="white-space: nowrap; display: flex; gap: 4px;">
                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="openStatusModal('${row.ID}', '${row.Estado}')">✏️ Estado</button>
                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="viewCreditoCuotas('${row.ID}')">👁️ Cuenta</button>
                </td>
            </tr>`;
            tbodyHtml += rowHtml;
        });
        tbody.innerHTML = tbodyHtml;
        
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center; color: var(--error);">Error al cargar créditos: ${e.message}</td></tr>`;
    }
}

// -------------------------------------------------------------
// System Actions Logic
// -------------------------------------------------------------
async function syncSystemStates() {
    const btn = document.getElementById('btn-sync-states');
    btn.disabled = true;
    btn.innerText = "Sincronizando...";

    try {
        const res = await fetch(`${API_URL}/api/v1/system/actualizar_estados`, {
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
