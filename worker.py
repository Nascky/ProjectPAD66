import redis
import json
import os
from sentence_transformers import SentenceTransformer
import numpy as np

BASE_JURIDICA_PATH = "base_juridica"
redis_client = redis.Redis(host='localhost', port=6379, db=0)
minilm_model = SentenceTransformer('all-MiniLM-L6-v2')

def ler_base_juridica(pasta_base=BASE_JURIDICA_PATH):
    artigos = []
    origens = []
    arquivos = [f for f in os.listdir(pasta_base) if f.endswith(".txt")]
    print(f"[DEBUG] Lendo base jurídica ({len(arquivos)} arquivos)...")
    for arquivo in arquivos:
        caminho = os.path.join(pasta_base, arquivo)
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()
            for bloco in texto.split("\n\n"):
                if bloco.strip():
                    artigos.append(bloco.strip())
                    origens.append(arquivo.replace(".txt", ""))  # Ex: RDBM, POP
    print(f"[DEBUG] Total de artigos carregados: {len(artigos)}")
    return artigos, origens

def classificar_artigos(relato, artigos, origens):
    print(f"[DEBUG] Classificando artigos para relato: {relato[:80]}...")
    emb_artigos = minilm_model.encode(artigos)
    emb_relato = minilm_model.encode([relato])
    scores = np.dot(emb_artigos, emb_relato.T).flatten()
    indices = scores.argsort()[::-1]
    artigos_infringidos = []
    artigos_defesa = []
    for idx in indices:
        artigo = artigos[idx]
        artigo_lower = artigo.lower()
        if any(palavra in artigo_lower for palavra in [
            "deixar de", "proibido", "vedado", "falta", "omissão", "descumprir"
        ]):
            artigos_infringidos.append(artigo)
        elif any(palavra in artigo_lower for palavra in [
            "direito", "garantido", "elogio", "atenuante", "bom comportamento", "boa conduta"
        ]):
            artigos_defesa.append(artigo)
        else:
            if len(artigos_infringidos) <= len(artigos_defesa):
                artigos_infringidos.append(artigo)
            else:
                artigos_defesa.append(artigo)
    print(f"[DEBUG] Artigos acusadores: {artigos_infringidos[:2]}")
    print(f"[DEBUG] Artigos de defesa: {artigos_defesa[:2]}")
    return artigos_infringidos[:5], artigos_defesa[:5]  # Limita para não encher demais

def worker():
    print("Worker iniciado. Esperando relatos na fila...")
    artigos, origens = ler_base_juridica(BASE_JURIDICA_PATH)
    while True:
        try:
            fila_result = redis_client.blpop('fila_pad66')
            if fila_result:
                _, item = fila_result
                pedido = json.loads(item.decode())
                print(f"\n[WORKER] Pedido recebido: {pedido}")
                user_id = pedido.get("user_id")
                relato = pedido.get("relato", "")
                print(f"[WORKER] Processando pedido de user_id: {user_id}")
                artigos_infringidos, artigos_defesa = classificar_artigos(relato, artigos, origens)
                resultado = {
                    "acusadores": artigos_infringidos,
                    "defesa": artigos_defesa
                }
                redis_client.set(f"resultado:{user_id}", json.dumps(resultado))
                print(f"[WORKER] Resultado salvo para user_id: {user_id}")
                # Debug: Lê o que foi salvo
                check = redis_client.get(f"resultado:{user_id}")
                print(f"[WORKER] Resultado no Redis: {check}\n")
        except Exception as e:
            print(f"[WORKER] Erro ao processar pedido: {e}")

if __name__ == "__main__":
    worker()
print("Worker parou? Isso não era pra acontecer!")
