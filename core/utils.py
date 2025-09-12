import streamlit as st
import base64
import io
import mimetypes

state=st.session_state

def rerun():
    """Request a rerun from anywhere in the app"""
    state.rerun = True

def check_rerun():
    """Check if rerun was requested and execute it"""
    if state.get('rerun',False):
        state.rerun = False
        st.rerun()

def short_id(length=8):
    import string, random
    return ''.join(random.choices(string.ascii_letters,k=length))

def bytesio_to_base64(data: io.BytesIO) -> str:
    """
    Convertit un objet io.BytesIO contenant une image en une chaîne base64
    avec préfixe data:...;base64, en utilisant l’extension dans data.name.
    """
    # Déterminer le type mime à partir de l’extension
    mime_type, _ = mimetypes.guess_type(getattr(data, "name", ""))
    if mime_type is None:
        mime_type = "application/octet-stream"

    # Revenir au début du flux si nécessaire
    data.seek(0)
    encoded_bytes = base64.b64encode(data.read())
    encoded_str = encoded_bytes.decode("ascii")

    return f"data:{mime_type};base64,{encoded_str}"


def base64_to_bytesio(b64_string: str) -> io.BytesIO:
    """
    Convertit une chaîne base64 (optionnellement avec préfixe data:...) en io.BytesIO.
    """
    # Si la chaîne contient un préfixe data:..., on le retire
    if b64_string.startswith("data:"):
        _, b64_data = b64_string.split(",", 1)
    else:
        b64_data = b64_string

    raw_bytes = base64.b64decode(b64_data)
    return io.BytesIO(raw_bytes)