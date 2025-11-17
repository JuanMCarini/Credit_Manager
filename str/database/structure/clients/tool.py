from str.database.connection import read_table


def validate_cuil(doc: str | int) -> int:
    s = "".join(ch for ch in str(doc) if ch.isdigit())
    if len(s) != 11:
        raise ValueError(f"⚠️⚠️⚠️ {doc} no es un CUIT/CUIL. ⚠️⚠️⚠️")

    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    digits = [int(ch) for ch in s]
    suma = 0
    for i, w in enumerate(weights):
        suma += digits[i] * w
    mod = suma % 11
    check = 11 - mod
    if check == 11:
        check = 0
    elif check == 10:
        check = 9
    return int(s)


def validate_dni_cuil(dni: str | int, cuil: str | int) -> tuple[int, int]:
    cuil = validate_cuil(cuil)
    dni = "".join(ch for ch in str(dni) if ch.isdigit())
    if len(dni) > 8:
        raise ValueError(f"⚠️⚠️⚠️ {dni} no es un DNI. ⚠️⚠️⚠️")
    else:
        dni = int(dni)

    if dni == cuil // 10 % 10**8:
        df = read_table("clients", "DNI")
        try:
            CUIL_DB = df.at[str(dni), "CUIL"]
            if str(cuil) != CUIL_DB:
                raise ValueError(
                    f"⚠️⚠️⚠️ The CUIL {cuil} and the DNI {dni} do not match with the database. ⚠️⚠️⚠️"
                )
        except KeyError:
            pass

        return dni, cuil
    else:
        raise ValueError(f"⚠️⚠️⚠️ This {dni} is not a DNI for the CUIL {cuil}. ⚠️⚠️⚠️")
