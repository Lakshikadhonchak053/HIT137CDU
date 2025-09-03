import os
from typing import Tuple

ALPHA_LOWER = "abcdefghijklmnopqrstuvwxyz"
ALPHA_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER_FIRST = set("abcdefghijklm")
LOWER_SECOND = set("nopqrstuvwxyz")
UPPER_FIRST = set("ABCDEFGHIJKLM")
UPPER_SECOND = set("NOPQRSTUVWXYZ")

def _shift_char(c: str, shift: int, alphabet: str) -> str:
    if c not in alphabet:
        return c
    n = len(alphabet)
    idx = alphabet.index(c)
    return alphabet[(idx + shift) % n]

def _encrypt_char(c: str, shift1: int, shift2: int) -> str:
    if c.islower():
        if c in LOWER_FIRST:
            return _shift_char(c, shift1 * shift2, ALPHA_LOWER)
        elif c in LOWER_SECOND:
            return _shift_char(c, -(shift1 + shift2), ALPHA_LOWER)
        else:
            return c
    elif c.isupper():
        if c in UPPER_FIRST:
            return _shift_char(c, -shift1, ALPHA_UPPER)
        elif c in UPPER_SECOND:
            return _shift_char(c, (shift2 ** 2), ALPHA_UPPER)
        else:
            return c
    else:
        return c

def _decrypt_char(c: str, shift1: int, shift2: int) -> str:
    if c.islower():
        cand1 = _shift_char(c, -(shift1 * shift2), ALPHA_LOWER)
        if cand1 in LOWER_FIRST:
            return cand1
        cand2 = _shift_char(c, (shift1 + shift2), ALPHA_LOWER)
        return cand2
    elif c.isupper():
        cand1 = _shift_char(c, shift1, ALPHA_UPPER)
        if cand1 in UPPER_FIRST:
            return cand1
        cand2 = _shift_char(c, -(shift2 ** 2), ALPHA_UPPER)
        return cand2
    else:
        return c

def encrypt_text(text: str, shift1: int, shift2: int) -> str:
    return "".join(_encrypt_char(c, shift1, shift2) for c in text)

def encrypt_text_with_meta(text: str, shift1: int, shift2: int) -> Tuple[str, str]:
    """Return encrypted text and sidecar metadata marking which rule was applied per char.

    Meta codes per character (same length as text):
    - 'l': original lowercase in a-m (shift forward by shift1*shift2)
    - 'L': original lowercase in n-z (shift backward by shift1+shift2)
    - 'u': original uppercase in A-M (shift backward by shift1)
    - 'U': original uppercase in N-Z (shift forward by shift2**2)
    - '0': non-alphabetic (unchanged)
    """
    encrypted_chars = []
    meta_chars = []
    for c in text:
        if c.islower():
            if c in LOWER_FIRST:
                encrypted_chars.append(_shift_char(c, shift1 * shift2, ALPHA_LOWER))
                meta_chars.append('l')
            elif c in LOWER_SECOND:
                encrypted_chars.append(_shift_char(c, -(shift1 + shift2), ALPHA_LOWER))
                meta_chars.append('L')
            else:
                encrypted_chars.append(c)
                meta_chars.append('0')
        elif c.isupper():
            if c in UPPER_FIRST:
                encrypted_chars.append(_shift_char(c, -shift1, ALPHA_UPPER))
                meta_chars.append('u')
            elif c in UPPER_SECOND:
                encrypted_chars.append(_shift_char(c, (shift2 ** 2), ALPHA_UPPER))
                meta_chars.append('U')
            else:
                encrypted_chars.append(c)
                meta_chars.append('0')
        else:
            encrypted_chars.append(c)
            meta_chars.append('0')
    return "".join(encrypted_chars), "".join(meta_chars)

def decrypt_text(text: str, shift1: int, shift2: int) -> str:
    return "".join(_decrypt_char(c, shift1, shift2) for c in text)

def decrypt_text_with_meta(ciphertext: str, metadata: str, shift1: int, shift2: int) -> str:
    """Deterministically decrypt using sidecar metadata produced during encryption."""
    if len(ciphertext) != len(metadata):
        raise ValueError("Ciphertext and metadata lengths do not match")
    result_chars = []
    for c, m in zip(ciphertext, metadata):
        if m == 'l':
            result_chars.append(_shift_char(c, -(shift1 * shift2), ALPHA_LOWER))
        elif m == 'L':
            result_chars.append(_shift_char(c, (shift1 + shift2), ALPHA_LOWER))
        elif m == 'u':
            result_chars.append(_shift_char(c, shift1, ALPHA_UPPER))
        elif m == 'U':
            result_chars.append(_shift_char(c, -(shift2 ** 2), ALPHA_UPPER))
        else:
            result_chars.append(c)
    return "".join(result_chars)

def _paths() -> Tuple[str, str, str, str]:
    base = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(base, "raw_text.txt")
    enc_path = os.path.join(base, "encrypted_text.txt")
    dec_path = os.path.join(base, "decrypted_text.txt")
    meta_path = os.path.join(base, "encryption_meta.txt")
    return raw_path, enc_path, dec_path, meta_path

def encrypt_file(shift1: int, shift2: int) -> None:
    raw_path, enc_path, _, meta_path = _paths()
    with open(raw_path, "r", encoding="utf-8") as f:
        raw = f.read()
    enc, meta = encrypt_text_with_meta(raw, shift1, shift2)
    with open(enc_path, "w", encoding="utf-8") as f:
        f.write(enc)
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(meta)
    print(f"Encrypted -> {enc_path}")

def decrypt_file(shift1: int, shift2: int) -> None:
    _, enc_path, dec_path, meta_path = _paths()
    with open(enc_path, "r", encoding="utf-8") as f:
        enc = f.read()
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = f.read()
    dec = decrypt_text_with_meta(enc, meta, shift1, shift2)
    with open(dec_path, "w", encoding="utf-8") as f:
        f.write(dec)
    print(f"Decrypted -> {dec_path}")

def verify_decryption() -> bool:
    raw_path, _, dec_path, _ = _paths()
    with open(raw_path, "r", encoding="utf-8") as f:
        raw = f.read()
    with open(dec_path, "r", encoding="utf-8") as f:
        dec = f.read()
    ok = raw == dec
    print("Verification:", "SUCCESS" if ok else "FAILURE")
    return ok

def _read_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Please enter an integer.")

def main():
    shift1 = _read_int("Enter shift1 (integer): ")
    shift2 = _read_int("Enter shift2 (integer): ")
    encrypt_file(shift1, shift2)
    decrypt_file(shift1, shift2)
    verify_decryption()

if __name__ == "__main__":
    main()
