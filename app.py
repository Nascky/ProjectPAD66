from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from utils import carregar_base_rdbm, carregar_prompt
from werkzeug.utils import secure_filename
import subprocess
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "pad66-secret"

CAMINHO_RDBM = "base_juridica/RDBM.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET"])
def formulario():
    return render_template("form.html")

@app.route("/gerar", methods=["POST"])
def gerar():
    # Salvar dados do formulário
    session["dados"] = {
        "nome": request.form.get("nome"),
        "id": request.form.get("id"),
        "posto": request.form.get("posto"),
        "batalhao": request.form.get("batalhao"),
        "tempo_servico": request.form.get("tempo_servico"),
        "elogios": request.form.get("elogios"),
        "numero_notificacao": request.form.get("numero_notificacao"),
        "relato": request.form.get("relato")
    }

    # Verifica se veio arquivo
    arquivo = request.files.get("arquivo")
    if arquivo and arquivo.filename != "":
        nome_seguro = secure_filename(arquivo.filename)
        caminho_arquivo = os.path.join(UPLOAD_FOLDER, nome_seguro)
        arquivo.save(caminho_arquivo)
        session["arquivo_path"] = caminho_arquivo  # pode usar na defesa se quiser

    return redirect(url_for("loading"))

@app.route("/loading")
def loading():
    return render_template("loading.html")

@app.route("/defesa", methods=["POST"])
def defesa():
    dados = session.get("dados")
    if not dados:
        return jsonify({"erro": "Dados não encontrados na sessão"}), 400

    prompt_base = carregar_prompt()
    base_rdbm = carregar_base_rdbm(CAMINHO_RDBM)

    prompt_completo = f"""{prompt_base}

REGULAMENTO DISCIPLINAR DA BRIGADA MILITAR (RDBM):
{base_rdbm}
"""

    relato_do_militar = f"""
NOME: {dados['nome']}
ID: {dados['id']}
POSTO: {dados['posto']}
BATALHÃO: {dados['batalhao']}
TEMPO DE SERVIÇO: {dados['tempo_servico']}
ÚLTIMO ELOGIO: {dados['elogios']}
Nº DA NOTIFICAÇÃO DO PAD: {dados['numero_notificacao']}

RELATO DOS FATOS:
{dados['relato']}
"""

    try:
        resposta = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt_completo},
                {"role": "user", "content": relato_do_militar}
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
