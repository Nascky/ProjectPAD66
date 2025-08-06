from flask import Flask, render_template, request
import requests

app = Flask(__name__)
app.secret_key = "pad66-secret"

# CONFIGURE aqui o IP e porta do Servidor B!
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

    # Consulta o Servidor B
    artigos = buscar_artigos_servidor_b(relato)
    artigos_infringidos = artigos.get("artigos_infringidos", [])
    artigos_defesa = artigos.get("artigos_defesa", [])

    return render_template(
        "resultado.html",
        artigos_infracao=artigos_infringidos,
        artigos_defesa=artigos_defesa
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
