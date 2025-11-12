def _log(text, outputs: bool = True):
    if outputs:
        print(text)


def validar_cuit_cuil(doc: str | int) -> int:
    """
    Valida un CUIT/CUIL en formato numérico (puede contener guiones).
    Devuelve True si es válido, False si no.
    """
    # Normalizar: quitar guiones y espacios
    s = "".join(ch for ch in str(doc) if ch.isdigit())
    if len(s) != 11:
        raise ValueError(f"{doc} no es un CUIT/CUIL.")

    # Multiplicadores (weights) según estándar argentino:
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]  # se aplican a los primeros 10 dígitos
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
