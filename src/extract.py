import sys

def extract(fpath: str):
    with open(fpath, "r") as f:
        text = f.read()
    chunks = chunk_text(text)
    for chunk in chunks:
        print(chunk)

def chunk_text(text: str) -> list[str]:
    return text.split(".")

print(chunk_text("a, b, c, d, \n e f g"))



if __name__ == "__main__":
    extract(sys.argv[1])