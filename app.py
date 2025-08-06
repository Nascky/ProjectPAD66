from flask import Flask, render_template, request
import requests
import subprocess
import os
import sys

app = Flask(__name__)
app.secret_key = "pad66-secret"

# CONFIGURE o IP do Servidor B
SERVIDOR_B_URL = "http://172.31.46.113:5001/search"  # Troque pelo IP do seu Servidor B

@app.route("/")
def index():
    return render_template("form.html")

def buscar_artigos_servidor_b(relato):
    try:
        payload = {"relato": relato}
        resp = requests.post(SERVIDOR_B_URL, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Erro ao buscar artigos no B: {resp.status_code} {resp.text}")
            return {"artigos_infringidos": [], "artigos_defesa": []}
    except Exception as e:
        print(f"Falha ao conectar ao servidor B: {e}")
        return {"artigos_infringidos": [], "artigos_defesa": []}

@app.route("/gerar", methods=["POST"])
def gerar():
    relato = request.form.get("relato")
    if not relato:
        return "Relato obrigatório", 400

    artigos = buscar_artigos_servidor_b(relato)
    artigos_infringidos = artigos.get("artigos_infringidos", [])
    artigos_defesa = artigos.get("artigos_defesa", [])

    return render_template(
        "resultado.html",
        artigos_infracao=artigos_infringidos,
        artigos_defesa=artigos_defesa
    )

# --- WEBHOOK PARA AUTO DEPLOY VIA GITHUB + RESTART APP ---
@app.route("/webhook", methods=["POST"])
def webhook():
    """Endpoint para receber webhook do GitHub, fazer git pull e reiniciar a aplicação."""
    try:
        resultado = subprocess.check_output(
            ["git", "-C", "/home/ubuntu/ProjectPAD66", "pull"],
            stderr=subprocess.STDOUT
        )
        # Reinicia o processo do Flask
        os.execv(sys.executable, ['python3'] + sys.argv)
        return f"Atualizado com sucesso e app reiniciado:\n{resultado.decode()}", 200
    except subprocess.CalledProcessError as e:
        return f"Erro ao atualizar:\n{e.output.decode()}", 500

# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
