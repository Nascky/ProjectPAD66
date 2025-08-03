from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import subprocess
import os
import redis
import json

# Carrega variáveis de ambiente
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "pad66-secret"

UPLOAD_FOLDER = "uploads"
PROMPT_PAD66 = "prompts/prompt_pad66.txt"
BASE_JURIDICA_PATH = "base_juridica"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Redis setup
redis_client = redis.Redis(host='localhost', port=6379, db=0)

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
            for bloco in texto.split("\n\n"):
                if bloco.strip():
                    artigos.append(bloco.strip())
                    origens.append(arquivo.replace(".txt", ""))  # Ex: RDBM, POP
    return artigos, origens

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
    dados = {
        "nome": request.form.get("nome"),
        "id": request.form.get("id"),
        "posto": request.form.get("posto"),
        "batalhao": request.form.get("batalhao"),
        "tempo_servico": request.form.get("tempo_servico"),
        "elogios": request.form.get("elogios"),
        "numero_notificacao": request.form.get("numero_notificacao"),
        "relato": request.form.get("relato"),
    }
    user_id = session.get("user_id", os.urandom(8).hex())
    session["user_id"] = user_id
    # Coloca na fila do Redis
    redis_client.rpush('fila_pad66', json.dumps({"user_id": user_id, "dados": dados}))
    return redirect(url_for("loading"))

@app.route("/loading")
def loading():
    return render_template("loading.html")

@app.route("/defesa", methods=["POST"])
def defesa():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"erro": "Usuário não encontrado"}), 400
    resultado = redis_client.get(f"resultado:{user_id}")
    if resultado:
        session["defesa"] = resultado.decode()
        return jsonify({"ok": True})
    else:
        return jsonify({"ok": False})

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
