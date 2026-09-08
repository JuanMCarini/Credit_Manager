import psycopg2

def unify_accounts():
    conn = psycopg2.connect('postgresql://usuario_db:password_seguro@db:5432/credit_manager_db')
    cur = conn.cursor()

    # Find accounts with .0
    cur.execute("SELECT id, id_externo FROM cuentas_comitentes WHERE id_externo LIKE '%.0'")
    cuentas_punto_cero = cur.fetchall()

    print(f'Found {len(cuentas_punto_cero)} accounts ending in .0')

    for id_cero, id_ext_cero in cuentas_punto_cero:
        base_id_ext = id_ext_cero[:-2]  # Remove '.0'
        cur.execute("SELECT id FROM cuentas_comitentes WHERE id_externo = %s", (base_id_ext,))
        base_row = cur.fetchone()
        
        if base_row:
            base_id = base_row[0]
            print(f'Unifying {id_ext_cero} (id {id_cero}) -> {base_id_ext} (id {base_id})')
            
            # TitularidadCuentaComitente
            cur.execute("SELECT id, id_inversor FROM titularidad_cuenta_comitente WHERE id_cuenta_comitente = %s", (id_cero,))
            for t_row in cur.fetchall():
                t_id, inversor_id = t_row
                cur.execute("SELECT id FROM titularidad_cuenta_comitente WHERE id_cuenta_comitente = %s AND id_inversor = %s", (base_id, inversor_id))
                if cur.fetchone():
                    # Base account already has this investor, we can delete the duplicate link
                    cur.execute("DELETE FROM titularidad_cuenta_comitente WHERE id = %s", (t_id,))
                else:
                    # Reassign this investor link to the base account
                    cur.execute("UPDATE titularidad_cuenta_comitente SET id_cuenta_comitente = %s WHERE id = %s", (base_id, t_id))
                    
            # MovimientoDeuda
            cur.execute("UPDATE movimientos_deuda SET id_cuenta_comitente = %s WHERE id_cuenta_comitente = %s", (base_id, id_cero))
            
            # Delete old account
            cur.execute("DELETE FROM cuentas_comitentes WHERE id = %s", (id_cero,))
            print(f'Unified {id_ext_cero} into {base_id_ext}')
        else:
            print(f'Base account {base_id_ext} not found, stripping .0 from existing account.')
            cur.execute("UPDATE cuentas_comitentes SET id_externo = %s WHERE id = %s", (base_id_ext, id_cero))

    conn.commit()
    cur.close()
    conn.close()
    print('Done!')

if __name__ == "__main__":
    unify_accounts()
