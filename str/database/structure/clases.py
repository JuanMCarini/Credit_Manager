# database/structure/clases.py

import re


class Email:
    def __init__(self, address: str | None):
        if address is None:
            self.address = None
        else:
            # Normalize first
            cleaned = str(address).strip().upper()

            # Validate the cleaned version
            if self._is_valid(cleaned):
                self.address = cleaned
            else:
                self.address = None

    def _is_valid(self, value: str | None) -> bool:
        if value is None:
            return True
        pattern = r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$"
        if re.match(pattern, value) is not None:
            return True
        else:
            raise ValueError(f"⚠️⚠️⚠️ {value} is not a valid e-mail. ⚠️⚠️⚠️")

    def __str__(self):
        status = "valid" if self._is_valid(self.address) else "invalid"
        return f"Email({self.address!r}) is {status}"
