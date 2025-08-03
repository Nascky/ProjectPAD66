from flask import Flask, render_template, request, redirect, url_for, session
import os
from sentence_transformers import SentenceTransformer
import numpy as np

app = Flask(__name__)
app.secret_key = "pad66-secret"

BASE_JURIDICA_PATH = "base_juridica"
minilm_model = SentenceTransformer('all-MiniLM-L6-v2')

def ler_base_juridica(pasta_base=BASE_JURIDICA_PATH):
    artigos = []
    arquivos = [f for f in os.listdir(pasta_base) if f.endswith(".txt")]
    for arquivo in arquivos:
        caminho = os.path.join(pasta_base, arquivo)
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()
            for bloco in texto.split("\n\n"):
                if bloco.strip():
                    artigos.append(bloco.strip())
    return artigos

def classificar_artigos(relato, artigos):
    emb_artigos = minilm_model.encode(artigos)
    emb_relato = minilm_model.encode([relato])
    scores = np.dot(emb_artigos, emb_relato.T).flatten()
    indices = scores.argsort()[::-1]
    artigos_infringidos = []
    artigos_defesa = []
    for idx in indices:
        artigo = artigos[idx]
        artigo_lower = artigo.lower()
        if any(palavra in artigo_lower for palavra in ["deixar de", "proibido", "vedado", "falta", "omissão", "descumprir"]):
            artigos_infringidos.append(artigo)
        elif any(palavra in artigo_lower for palavra in ["direito", "garantido", "elogio", "atenuante", "bom comportamento", "boa conduta"]):
            artigos_defesa.append(artigo)
        else:
            if len(artigos_infringidos) <= len(artigos_defesa):
                artigos_infringidos.append(artigo)
            else:
                artigos_defesa.append(artigo)
    return artigos_infringidos[:5], artigos_defesa[:5]

@app.route("/gerar", methods=["POST"])
def gerar():
    relato = request.form.get("relato")
    artigos = ler_base_juridica(BASE_JURIDICA_PATH)
    acusadores, defesa = classificar_artigos(relato, artigos)
    # Simula 30s de espera (opcional)
    # import time; time.sleep(30)
    return render_template("resultado.html", artigos_infracao=acusadores, artigos_defesa=defesa)

# Os demais endpoints permanecem como antes...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
