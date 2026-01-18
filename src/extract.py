import sys

def extract(fpath: str):
    with open(fpath, "r") as f:
        text = f.read()
    chunks = chunk_text(text)
    for chunk in chunks:
        print(chunk)

# Improve chunking with chunk overlapping, paragraph accumulation (till the 2500 char limit)

def chunk_text(text: str) -> list[str]:
    # Split on paragraphs and at a max char size of 2500 chars
    paragraphs = text.split("\n\n")
    chunks = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        while len(paragraph) > 2500:
            chunk = paragraph[:2500]
            chunks.append(chunk)
            paragraph = paragraph[2500:]

        chunks.append(paragraph)

    return chunks

print(chunk_text("a, b, c, d, \n e f g"))



if __name__ == "__main__":
    extract(sys.argv[1])