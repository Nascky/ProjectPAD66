import redis
import json
from sentence_transformers import SentenceTransformer
import numpy as np
from openai import OpenAI
import os

PROMPT_PAD66 = "prompts/prompt_pad66.txt"
BASE_JURIDICA_PATH = "base_juridica"
os.environ["OPENAI_API_KEY"] = "<TUA_CHAVE_OPENAI>"  # Ou usa dotenv se preferir

redis_client = redis.Redis(host='localhost', port=6379, db=0)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
minilm_model = SentenceTransformer('all-MiniLM-L6-v2')

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
                    origens.append(arquivo.replace(".txt", ""))
    return artigos, origens

def buscar_artigos_semantico_minilm(relato, artigos, origens, limite=3):
    emb_artigos = minilm_model.encode(artigos)
    emb_relato = minilm_model.encode([relato])
    scores = np.dot(emb_artigos, emb_relato.T).flatten()
    top_idx = scores.argsort()[-limite:][::-1]
    return [(artigos[i], origens[i]) for i in top_idx]

def processar_defesa(user_id, dados):
    relato_do_militar = dados.get('relato', '')
    artigos, origens = ler_base_juridica(BASE_JURIDICA_PATH)
    artigos_e_origens = buscar_artigos_semantico_minilm(relato_do_militar, artigos, origens, limite=3)

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
    redis_client.set(f"resultado:{user_id}", conteudo)

def worker():
    print("Worker iniciado. Esperando relatos na fila...")
    while True:
        _, item = redis_client.blpop('fila_pad66')
        pedido = json.loads(item.decode())
        user_id = pedido["user_id"]
        dados = pedido["dados"]
        try:
            processar_defesa(user_id, dados)
        except Exception as e:
            print(f"Erro ao processar defesa para {user_id}: {e}")

if __name__ == "__main__":
    worker()
