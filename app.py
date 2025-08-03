from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import subprocess
import os

from sklearn.feature_extraction.text import TfidfVectorizer

# Carrega variáveis de ambiente
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "pad66-secret"

UPLOAD_FOLDER = "uploads"
PROMPT_PAD66 = "prompts/prompt_pad66.txt"
BASE_JURIDICA_PATH = "base_juridica"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def carregar_prompt_pad66():
    with open(PROMPT_PAD66, "r", encoding="utf-8") as f:
        return f.read()

def ler_base_juridica(pasta_base=BASE_JURIDICA_PATH):
    artigos = []
    origens = []
    arquivos = [f for f in os.listdir(pasta_base) if f.endswith(".txt")]
    for arquivo in arquivos:
        caminho = os.path.join(pasta_base, arquivo)
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()
            # Cada artigo separado por 2 ENTER
            for bloco in texto.split("\n\n"):
                if bloco.strip():
                    artigos.append(bloco.strip())
                    origens.append(arquivo.replace(".txt", ""))  # Ex: RDBM, POP
    return artigos, origens

def buscar_artigos_mais_relevantes(relato, artigos, origens, limite=3):
    # Busca semântica por TF-IDF
    textos = [relato] + artigos
    tfidf = TfidfVectorizer().fit_transform(textos)
    scores = (tfidf[0] * tfidf[1:].T).toarray()[0]
    top_idx = scores.argsort()[-limite:][::-1]
    return [(artigos[i], origens[i]) for i in top_idx]

@app.route("/")
def pagina_inicial():
    return render_template("inicial.html")

@app.route("/tipo-envio")
def tipo_envio():
    return render_template("escolha.html")

@app.route("/enviar")
def enviar_documento():
    return render_template("imagem.html")

@app.route("/escrever")
def escrever_relato():
    return render_template("form.html")

@app.route("/processar-documento", methods=["POST"])
def processar_documento():
    arquivo = request.files.get("arquivo")
    if not arquivo or arquivo.filename == "":
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    nome_seguro = secure_filename(arquivo.filename)
    caminho_arquivo = os.path.join(UPLOAD_FOLDER, nome_seguro)
    arquivo.save(caminho_arquivo)

    try:
        imagem = Image.open(caminho_arquivo)
        texto_extraido = pytesseract.image_to_string(imagem, lang='por')
    except Exception as e:
        return jsonify({"erro": f"Erro ao processar imagem: {str(e)}"}), 500

    session["dados"] = {
        "relato": texto_extraido
    }

    return redirect(url_for("loading"))

@app.route("/gerar", methods=["POST"])
def gerar():
    session["dados"] = {
        "nome": request.form.get("nome"),
        "id": request.form.get("id"),
        "posto": request.form.get("posto"),
        "batalhao": request.form.get("batalhao"),
        "tempo_servico": request.form.get("tempo_servico"),
        "elogios": request.form.get("elogios"),
        "numero_notificacao": request.form.get("numero_notificacao"),
        "relato": request.form.get("relato"),
    }
    return redirect(url_for("loading"))

@app.route("/loading")
def loading():
    return render_template("loading.html")

@app.route("/defesa", methods=["POST"])
def defesa():
    dados = session.get("dados")
    if not dados:
        return jsonify({"erro": "Dados não encontrados na sessão"}), 400

    relato_do_militar = dados.get('relato', '')

    # Busca semântica local: pega 3 artigos mais próximos do relato
    artigos, origens = ler_base_juridica(BASE_JURIDICA_PATH)
    artigos_e_origens = buscar_artigos_mais_relevantes(relato_do_militar, artigos, origens, limite=3)

    artigos_formatados = ""
    for artigo, origem in artigos_e_origens:
        artigos_formatados += f"\n---\n[Origem: {origem}]\n{artigo}\n"

    prompt_completo = f"""{carregar_prompt_pad66()}

📑 Artigos mais relevantes encontrados na base jurídica:
{artigos_formatados}

DADOS DO MILITAR:
- Graduação/Posto: {dados.get('posto')}
- Nome completo: {dados.get('nome')}
- ID: {dados.get('id')}
- Número da notificação: {dados.get('numero_notificacao')}
- Batalhão: {dados.get('batalhao')}
- Tempo de serviço (opcional): {dados.get('tempo_servico')}
- Elogios (opcional): {dados.get('elogios')}
"""

    try:
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt_completo},
                {"role": "user", "content": f"""
Considere os artigos e dados do militar acima.
Redija uma defesa conforme instruções do prompt, utilizando linguagem técnica, estrutura formal, citações jurídicas (indicando origem de cada artigo, ex: RDBM, POP etc.) e argumentação de advogado, mas em primeira pessoa, como se fosse o próprio militar.
Nunca copie o relato original — reescreva de forma técnica e elegante.
RELATO DOS FATOS:
{relato_do_militar}
"""}
            ],
            temperature=0.5
        )
        conteudo = resposta.choices[0].message.content
        session["defesa"] = conteudo
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/resultado")
def resultado():
    conteudo = session.get("defesa", "Defesa não encontrada.")
    return render_template("resultado.html", resultado=conteudo)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        print("Recebido webhook do GitHub... executando git pull")
        subprocess.run(["git", "pull"], cwd="/home/ubuntu/ProjectPAD66")
        return "Atualizado com sucesso", 200
    except Exception as e:
        return f"Erro no webhook: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
