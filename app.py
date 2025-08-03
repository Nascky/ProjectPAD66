from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os, json, redis, subprocess
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract

app = Flask(__name__)
app.secret_key = "pad66-secret"

UPLOAD_FOLDER = "uploads"
BASE_JURIDICA_PATH = "base_juridica"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Timer para fila
TEMPO_MINIMO = 30
TEMPO_MEDIO_PROCESSO = 3

def get_posicao_na_fila(user_id):
    fila = redis_client.lrange('fila_pad66', 0, -1)
    for i, item in enumerate(fila):
        pedido = json.loads(item.decode())
        if pedido['user_id'] == user_id:
            return i
    return -1

@app.route("/fila-posicao")
def fila_posicao():
    user_id = session.get("user_id")
    posicao = get_posicao_na_fila(user_id)
    if posicao == -1:
        return jsonify({"posicao": 0, "tempo_estimado": TEMPO_MINIMO})
    pessoas_na_frente = posicao
    tempo = TEMPO_MINIMO + (pessoas_na_frente * TEMPO_MEDIO_PROCESSO)
    return jsonify({"posicao": pessoas_na_frente + 1, "tempo_estimado": tempo})

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
    relato = request.form.get("relato")
    user_id = session.get("user_id", os.urandom(8).hex())
    session["user_id"] = user_id
    redis_client.rpush('fila_pad66', json.dumps({"user_id": user_id, "relato": relato}))
    return redirect(url_for("loading"))

@app.route("/loading")
def loading():
    return render_template("loading.html")

@app.route("/defesa", methods=["POST"])
def defesa():
    user_id = session.get("user_id")
    resultado = redis_client.get(f"resultado:{user_id}")
    if resultado:
        return jsonify({"ok": True})
    else:
        return jsonify({"ok": False})

@app.route("/resultado")
def resultado():
    user_id = session.get("user_id")
    resultado = redis_client.get(f"resultado:{user_id}")
    artigos_infracao = []
    artigos_defesa = []
    if resultado:
        res = json.loads(resultado.decode())
        artigos_infracao = res.get("acusadores", [])
        artigos_defesa = res.get("defesa", [])
    return render_template("resultado.html", artigos_infracao=artigos_infracao, artigos_defesa=artigos_defesa)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        print("Recebido webhook do GitHub... executando deploy.sh")
        subprocess.run(["/home/ubuntu/ProjectPAD66/deploy.sh"])
        return "Atualizado com sucesso", 200
    except Exception as e:
        return f"Erro no webhook: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
