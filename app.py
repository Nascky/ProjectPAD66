from flask import Flask, render_template, request
import requests
import subprocess
import os
import sys

app = Flask(__name__)
app.secret_key = "pad66-secret"

# IP público e endpoint do Server B
SERVIDOR_B_URL = "http://18.223.160.115:5000/api/buscar-artigos"  # Atualizado

@app.route("/")
def index():
    return render_template("form.html")

def buscar_artigos_servidor_b(relato):
    """
    Envia o relato do usuário para o servidor B e recebe os artigos relevantes.
    """
    try:
        payload = {"relato": relato}
        resp = requests.post(SERVIDOR_B_URL, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Erro ao buscar artigos no B: {resp.status_code} {resp.text}")
            return {"artigos": []}
    except Exception as e:
        print(f"Falha ao conectar ao servidor B: {e}")
        return {"artigos": []}

@app.route("/gerar", methods=["POST"])
def gerar():
    relato = request.form.get("relato")
    if not relato:
        return "Relato obrigatório", 400

    artigos = buscar_artigos_servidor_b(relato)
    lista_artigos = artigos.get("artigos", [])

    # Ajuste conforme seu resultado.html espera as variáveis!
    return render_template(
        "resultado.html",
        resultado="\n\n".join(lista_artigos)
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
