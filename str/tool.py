# tool.py
log = True


def _log(text, outputs: bool = True):
    if outputs:
        print(text)


def validate_email(email: str | None) -> str | None:
    if email is None or str(email).strip() == "":
        return None
    elif "@" not in email or ".com" not in email:
        raise ValueError(f"Invalid email address: {email}")
    else:
        email = email.strip()
        return email
