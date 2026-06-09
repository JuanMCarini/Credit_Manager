import re

file_path = r'd:\Repositorios\Credit_Manager\frontend\main.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update viewClientCuentaCorriente
new_client_headers = '''
        excelFilters['table-cliente-cta-cte'] = {};
        const headers = ["Crédito (ID)", "N° Cuota", "Vencimiento", "Capital", "Interés", "IVA", "Total Esperado", "Cobrado", "Saldo Pendiente", "Estado"];
        let theadHtml = "<tr>";
        headers.forEach((h, i) => {
            theadHtml += `<th><div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;"><span>${h}</span><span class="filter-icon filter-icon-table-cliente-cta-cte" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-cliente-cta-cte', 'cliente-cta-cte-headers')">▼</span></div></th>`;
        });
        theadHtml += "</tr>";
        document.getElementById('cliente-cta-cte-headers').innerHTML = theadHtml;
'''
content = content.replace('''        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay cuotas registradas para este cliente.</td></tr>';
            return;
        }

        let html = "";''', '''        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay cuotas registradas para este cliente.</td></tr>';
            document.getElementById('cliente-cta-cte-headers').innerHTML = '';
            return;
        }
''' + new_client_headers + '''
        let html = "";''')

content = content.replace('''        data.forEach(c => {
            const extStr = c.id_externo && c.id_externo !== '-' ? ` (${c.id_externo})` : '';
            const creditoLabel = `#${c.credito_id}${extStr}`;

            html += `<tr>''', '''        data.forEach(c => {
            const extStr = c.id_externo && c.id_externo !== '-' ? ` (${c.id_externo})` : '';
            const creditoLabel = `#${c.credito_id}${extStr}`;

            html += `<tr class="main-row">''')

content = content.replace('''            if (c.detalle_cobranzas && c.detalle_cobranzas.length > 0) {
                c.detalle_cobranzas.forEach(cob => {
                    html += `<tr style="background: rgba(255, 255, 255, 0.02); font-size: 12px; color: var(--text-secondary);">''', '''            if (c.detalle_cobranzas && c.detalle_cobranzas.length > 0) {
                c.detalle_cobranzas.forEach(cob => {
                    html += `<tr class="sub-row" style="background: rgba(255, 255, 255, 0.02); font-size: 12px; color: var(--text-secondary);">''')


# 2. Update viewCreditoCuotas
new_credit_headers = '''
        excelFilters['table-cuotas'] = {};
        const headers = ["N°", "Vencimiento", "Capital", "Interés", "IVA", "Total Esperado", "Cobrado", "Saldo Pendiente", "Estado"];
        let theadHtml = "<tr>";
        headers.forEach((h, i) => {
            theadHtml += `<th><div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;"><span>${h}</span><span class="filter-icon filter-icon-table-cuotas" data-col="${i}" onclick="openExcelFilter(event, ${i}, 'table-cuotas', 'cuotas-headers')">▼</span></div></th>`;
        });
        theadHtml += "</tr>";
        document.getElementById('cuotas-headers').innerHTML = theadHtml;
'''
content = content.replace('''        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay cuotas registradas para este crédito.</td></tr>';
            return;
        }

        let html = "";''', '''        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" style="text-align:center;">No hay cuotas registradas para este crédito.</td></tr>';
            document.getElementById('cuotas-headers').innerHTML = '';
            return;
        }
''' + new_credit_headers + '''
        let html = "";''')

content = content.replace('''        data.forEach(c => {
            html += `<tr>''', '''        data.forEach(c => {
            html += `<tr class="main-row">''')

content = content.replace('''            if (c.detalle_cobranzas && c.detalle_cobranzas.length > 0) {
                c.detalle_cobranzas.forEach(cob => {
                    html += `<tr style="background: rgba(255, 255, 255, 0.02); font-size: 12px; color: var(--text-secondary);">''', '''            if (c.detalle_cobranzas && c.detalle_cobranzas.length > 0) {
                c.detalle_cobranzas.forEach(cob => {
                    html += `<tr class="sub-row" style="background: rgba(255, 255, 255, 0.02); font-size: 12px; color: var(--text-secondary);">''')


# 3. Add sort functionality to openExcelFilter
sort_buttons = '''    let html = `
        <div style="display: flex; gap: 8px; margin-bottom: 8px;">
            <button class="btn-secondary" style="font-size: 11px; flex: 1; padding: 4px;" onclick="sortExcelFilter(event, ${colIndex}, '${tableId}', 'asc')">↑ Ascendente</button>
            <button class="btn-secondary" style="font-size: 11px; flex: 1; padding: 4px;" onclick="sortExcelFilter(event, ${colIndex}, '${tableId}', 'desc')">↓ Descendente</button>
        </div>
        <div style="margin-bottom: 8px;">'''
content = content.replace('''    let html = `
        <div style="margin-bottom: 8px;">''', sort_buttons)


# 4. Fix runAllExcelFilters
run_all_filters_fix = '''function runAllExcelFilters(tableId, headerId) {
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
        const tds = tr.getElementsByTagName("td");'''
content = content.replace('''function runAllExcelFilters(tableId, headerId) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;
    const trs = tbody.getElementsByTagName("tr");

    for (let i = 0; i < trs.length; i++) {
        let rowMatch = true;
        const tds = trs[i].getElementsByTagName("td");''', run_all_filters_fix)

content = content.replace('''                if (!match) {
                    rowMatch = false;
                    break;
                }
            }
        }
        trs[i].style.display = rowMatch ? "" : "none";
    }''', '''                if (!match) {
                    rowMatch = false;
                    break;
                }
            }
        }
        lastMainRowMatch = rowMatch;
        tr.style.display = rowMatch ? "" : "none";
    }''')

# 5. Add sortExcelFilter
sort_func = '''
window.sortExcelFilter = function(e, colIndex, tableId, direction) {
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
        let clean = val.replace(/[$%\\s]/g, '').replace(/\\./g, '').replace(',', '.');
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
        
        if (typeof aNum === 'string' && aVal.match(/^\\d{4}-\\d{2}-\\d{2}$/)) {
            aNum = new Date(aVal).getTime();
            bNum = new Date(bVal).getTime();
        }
        
        if (aNum === bNum) return 0;
        
        let comparison = 0;
        if (typeof aNum === 'number' && typeof bNum === 'number') {
            comparison = aNum > bNum ? 1 : -1;
        } else {
            comparison = aVal.localeCompare(bVal, undefined, {numeric: true});
        }
        
        return direction === 'asc' ? comparison : -comparison;
    });
    
    groups.forEach(g => {
        tbody.appendChild(g.mainRow);
        g.subRows.forEach(sr => tbody.appendChild(sr));
    });
    
    closeExcelFilter();
};

'''

content = content.replace('function closeExcelFilter()', sort_func + 'function closeExcelFilter()')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Script finished successfully')
