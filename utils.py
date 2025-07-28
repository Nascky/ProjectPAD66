import os
import fitz  # PyMuPDF

BASE_DIR = "base_juridica"

def extrair_texto_pdf(caminho_pdf):
    texto = ""
    with fitz.open(caminho_pdf) as pdf:
        for pagina in pdf:
            texto += pagina.get_text()
    return texto

def carregar_base_juridica():
    textos = []
    for arquivo in os.listdir(BASE_DIR):
        caminho = os.path.join(BASE_DIR, arquivo)

        if arquivo.endswith(".pdf"):
            print(f"[PDF] Lendo: {arquivo}")
            textos.append(extrair_texto_pdf(caminho))

        elif arquivo.endswith(".txt"):
            print(f"[TXT] Lendo: {arquivo}")
            with open(caminho, "r", encoding="utf-8") as f:
                textos.append(f.read())

    return "\n\n".join(textos)
def carregar_base_rdbm(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        texto = f.read()

    # Limita o tamanho para evitar estouro de tokens
    return texto[:14000]
def carregar_prompt():
    with open("prompts/prompt_pad66.txt", "r", encoding="utf-8") as f:
        return f.read()
