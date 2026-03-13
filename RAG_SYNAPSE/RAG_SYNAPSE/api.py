import os
import json
import glob
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
import ollama

# --- CONFIGURACIÓN ---
DOCS_DIR = "./documentos"
CHROMA_PATH = "./mi_base_datos"
LLM_MODEL = "llama3:8b"

app = FastAPI(title="Asistente RAG Puro (Sin LangChain)")

# CORS para el frontend
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Creamos las carpetas si no existen para evitar errores
os.makedirs(DOCS_DIR, exist_ok=True)

# Inicializamos la base de datos Chroma
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="memoria_asistente")

def fragmentar_texto(texto, tamano=1000, superposicion=150):
    """Función nativa de Python para cortar textos largos (Reemplaza a LangChain)"""
    fragmentos = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + tamano
        fragmentos.append(texto[inicio:fin])
        inicio += tamano - superposicion
    return fragmentos

def cargar_documentos_en_bd():
    """Lee JSON/TXT y los guarda en Chroma usando Ollama para los embeddings"""
    if collection.count() > 0:
        print("💾 Base de datos encontrada. Memoria lista.")
        return

    print("🆕 Primera vez iniciando: Procesando documentos...")
    archivos = glob.glob(f"{DOCS_DIR}/*.*")
    
    if not archivos:
        print(f"⚠️ Atención: No hay archivos en la carpeta '{DOCS_DIR}'.")
        return

    textos_a_guardar = []
    
    # Leer todos los archivos de la carpeta
    for ruta in archivos:
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                if ruta.endswith('.json'):
                    data = json.load(f)
                    contenido = json.dumps(data, ensure_ascii=False)
                else:
                    contenido = f.read()
                
                # Cortamos el texto
                textos_a_guardar.extend(fragmentar_texto(contenido))
        except Exception as e:
            print(f"Error leyendo {ruta}: {e}")

    if textos_a_guardar:
        print(f"🧠 Generando embeddings para {len(textos_a_guardar)} fragmentos con Ollama...")
        for i, fragmento in enumerate(textos_a_guardar):
            # Usamos la librería oficial de Ollama para convertir el texto en números
            emb = ollama.embeddings(model=LLM_MODEL, prompt=fragmento)['embedding']
            
            # Lo guardamos en ChromaDB
            collection.add(
                ids=[f"doc_{i}"],
                embeddings=[emb],
                documents=[fragmento]
            )
        print("✅ Base de datos vectorial creada con éxito.")

# Ejecutar la carga al iniciar el servidor
cargar_documentos_en_bd()

# --- RUTAS DE LA API ---
class PreguntaUsuario(BaseModel):
    query: str

@app.get("/")
def home():
    return {"estado": "🟢 Servidor RAG Puro en línea"}

@app.post("/ask")
def hacer_pregunta(request: PreguntaUsuario):
    pregunta = request.query
    
    try:
        # 1. Convertimos la pregunta del usuario en números (embedding)
        pregunta_emb = ollama.embeddings(model=LLM_MODEL, prompt=pregunta)['embedding']
        
        # 2. Buscamos en ChromaDB los 3 textos más similares
        resultados = collection.query(query_embeddings=[pregunta_emb], n_results=3)
        
        # Unimos los textos encontrados para dárselos a la IA
        contexto_encontrado = "\n".join(resultados['documents'][0])
        
        if not contexto_encontrado:
            contexto_encontrado = "No se encontró información relevante en los documentos."

        # 3. Creamos el Prompt y le preguntamos a Ollama (Chat)
        prompt_final = f"""Eres un asistente virtual profesional. Responde a la pregunta basándote ÚNICAMENTE en el contexto proporcionado. Si no sabes la respuesta, di que no tienes esa información.
        
        CONTEXTO:
        {contexto_encontrado}
        
        PREGUNTA:
        {pregunta}
        """

        # Generamos la respuesta
        respuesta_ia = ollama.chat(model=LLM_MODEL, messages=[
            {"role": "user", "content": prompt_final}
        ])
        
        return {"response": respuesta_ia['message']['content'], "status": "success"}

    except Exception as e:
        return {"response": f"Ocurrió un error: {str(e)}", "status": "error"}