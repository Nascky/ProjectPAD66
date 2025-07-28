import re

def carregar_rdbm_por_artigo(caminho="base_juridica/RDBM.txt"):
    with open(caminho, "r", encoding="utf-8") as f:
        texto = f.read()

    # Divide pelo padrão dos artigos (ex: Art. 3º)
    artigos = re.split(r"(Art\. ?\d+º?.*?)\n", texto)
    artigos_dict = {}

    for i in range(1, len(artigos), 2):
        titulo = artigos[i].strip()
        conteudo = artigos[i + 1].strip()
        artigos_dict[titulo] = conteudo

    return artigos_dict
