from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import subprocess
import os

# NOVO IMPORT!
from sklearn.feature_extraction.text import TfidfVectorizer

# Carrega variáveis de ambiente
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "pad66-secret"

UPLOAD_FOLDER = "uploads"
PROMPT_CONVERT = "prompts/convert.txt"
PROMPT_PAD66 = "prompts/prompt_pad66.txt"
BASE_JURIDICA_PATH = "base_juridica"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def carregar_prompt_convert():
    with open(PROMPT_CONVERT, "r", encoding="utf-8") as f:
        return f.read()

def carregar_prompt_pad66():
    with open(PROMPT_PAD66, "r", encoding="utf-8") as f:
        return f.read()

def converter_para_termos_juridicos(relato):
    prompt_base = carregar_prompt_convert()
    prompt = prompt_base.replace("{RELATO_DO_POLICIAL}", relato)
    resposta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt}
        ],
        temperature=0.2
    )
    termos = resposta.choices[0].message.content
    termos_lista = [t.strip() for t in termos.split(",") if t.strip()]
    # DEBUG: Exibe os termos extraídos do relato
    print("[DEBUG] Termos extraídos do relato:", termos_lista)
    return termos_lista

def buscar_artigos_mais_relevantes(relato, termos, pasta_base=BASE_JURIDICA_PATH, limite=2):
    artigos = []
    origens = []

    arquivos = [f for f in os.listdir(pasta_base) if f.endswith(".txt")]
    termos_baixo = [t.lower() for t in termos]

    for arquivo in arquivos:
        caminho = os.path.join(pasta_base, arquivo)
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()
            for bloco in texto.split("\n\n"):
                bloco_baixo = bloco.lower()
                if any(t in bloco_baixo for t in termos_baixo):
                    artigos.append(bloco.strip())
                    origens.append(arquivo.replace(".txt", ""))  # Ex: RDBM, POP

    if not artigos:
        print("[DEBUG] Nenhum artigo encontrado para os termos:", termos)
        return []
    # Busca por relevância usando TF-IDF
    textos = [relato] + artigos
    tfidf = TfidfVectorizer().fit_transform(textos)
    scores = (tfidf[0] * tfidf[1:].T).toarray()[0]
    top_idx = scores.argsort()[-limite:][::-1]

    print("[DEBUG] Artigos encontrados para o relato:")
    for i in top_idx:
        print("-----")
        print("Origem:", origens[i])
        print(artigos[i])
        print("-----")

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

    termos_juridicos = converter_para_termos_juridicos(texto_extraido)
    session["dados"] = {
        "relato": texto_extraido,
        "termos_juridicos": termos_juridicos
    }

    return redirect(url_for("loading"))

@app.route("/gerar", methods=["POST"])
def gerar():
    relato = request.form.get("relato")
    termos_juridicos = converter_para_termos_juridicos(relato)

    session["dados"] = {
        "nome": request.form.get("nome"),
        "id": request.form.get("id"),
        "posto": request.form.get("posto"),
        "batalhao": request.form.get("batalhao"),
        "tempo_servico": request.form.get("tempo_servico"),
        "elogios": request.form.get("elogios"),
        "numero_notificacao": request.form.get("numero_notificacao"),
        "relato": relato,
        "termos_juridicos": termos_juridicos
    }

    arquivo = request.files.get("arquivo")
    if arquivo and arquivo.filename != "":
        nome_seguro = secure_filename(arquivo.filename)
        caminho_arquivo = os.path.join(UPLOAD_FOLDER, nome_seguro)
        arquivo.save(caminho_arquivo)
        session["arquivo_path"] = caminho_arquivo

    return redirect(url_for("loading"))

@app.route("/loading")
def loading():
    return render_template("loading.html")

@app.route("/defesa", methods=["POST"])
def defesa():
    dados = session.get("dados")
    if not dados:
        return jsonify({"erro": "Dados não encontrados na sessão"}), 400

    termos_juridicos = dados.get("termos_juridicos", [])
    relato_do_militar = dados.get('relato', '')

    artigos_e_origens = buscar_artigos_mais_relevantes(
        relato_do_militar,
        termos_juridicos,
        pasta_base=BASE_JURIDICA_PATH,
        limite=2
    )
    artigos_formatados = ""
    for artigo, origem in artigos_e_origens:
        artigos_formatados += f"\n---\n[Origem: {origem}]\n{artigo}\n"

    prompt_completo = f"""{carregar_prompt_pad66()}

---
📚 Termos extraídos do relato:
{', '.join(termos_juridicos)}

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
Considere os termos, artigos e dados do militar acima.
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
