from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from utils import carregar_base_rdbm, carregar_prompt
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import subprocess
import os

# Carrega variáveis de ambiente
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "pad66-secret"

# Caminhos
CAMINHO_RDBM = "base_juridica/RDBM.txt"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Página inicial com explicação do projeto
@app.route("/")
def pagina_inicial():
    return render_template("inicial.html")

# Página para escolher envio de relato ou arquivo
@app.route("/tipo-envio")
def tipo_envio():
    return render_template("escolha.html")

# Página para enviar documento
@app.route("/enviar")
def enviar_documento():
    return render_template("imagem.html")

# Página para preencher relato manualmente
@app.route("/escrever")
def escrever_relato():
    return render_template("form.html")

# OCR real a partir do upload do documento
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

# Rota que recebe os dados manuais do formulário
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
        "relato": request.form.get("relato")
    }

    # Salva arquivo se existir
    arquivo = request.files.get("arquivo")
    if arquivo and arquivo.filename != "":
        nome_seguro = secure_filename(arquivo.filename)
        caminho_arquivo = os.path.join(UPLOAD_FOLDER, nome_seguro)
        arquivo.save(caminho_arquivo)
        session["arquivo_path"] = caminho_arquivo

    return redirect(url_for("loading"))

# Página de carregamento com o cronômetro
@app.route("/loading")
def loading():
    return render_template("loading.html")

# Geração da defesa com IA
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
NOME: {dados.get('nome')}
ID: {dados.get('id')}
POSTO: {dados.get('posto')}
BATALHÃO: {dados.get('batalhao')}
TEMPO DE SERVIÇO: {dados.get('tempo_servico')}
ÚLTIMO ELOGIO: {dados.get('elogios')}
Nº DA NOTIFICAÇÃO DO PAD: {dados.get('numero_notificacao')}

RELATO DOS FATOS:
{dados['relato']}
"""

    try:
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
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

# Exibição da defesa gerada
@app.route("/resultado")
def resultado():
    conteudo = session.get("defesa", "Defesa não encontrada.")
    return render_template("resultado.html", resultado=conteudo)

# Webhook para atualizar o projeto via GitHub
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
