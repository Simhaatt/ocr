import random
import unicodedata

# Simple noise generator for OCR-like variations

def drop_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")


def typo(s: str, rate=0.05):
    letters = list(s)
    for i in range(len(letters)):
        if random.random() < rate and letters[i].isalpha():
            letters[i] = random.choice("abcdefghijklmnopqrstuvwxyz")
    return "".join(letters)


def swap_tokens(s: str, rate=0.2):
    toks = s.split()
    if len(toks) > 1 and random.random() < rate:
        i = random.randrange(len(toks)-1)
        toks[i], toks[i+1] = toks[i+1], toks[i]
    return " ".join(toks)


def punct_noise(s: str):
    return s.replace(",", " ").replace(".", " ").replace("/", " ")


def confuse_digits(s: str):
    return s.replace("0", "O").replace("1", "I")


def make_noisy(record: dict) -> dict:
    out = dict(record)
    if out.get("name"):
        out["name"] = swap_tokens(typo(drop_accents(out["name"])) )
    if out.get("address"):
        out["address"] = swap_tokens(punct_noise(typo(drop_accents(out["address"])) ))
    if out.get("phone"):
        out["phone"] = confuse_digits(out["phone"])  # simplistic
    return out

if __name__ == "__main__":
    clean = {
        "name": "Ramesh Kumar",
        "dob": "19-04-2001",
        "phone": "9876543210",
        "address": "B12/3 Gandhi Street MG Road",
        "gender": "male",
    }
    print("CLEAN:", clean)
    print("NOISY:", make_noisy(clean))
