# Librerías necesarias para servidor HTTP, manejo de archivos y procesamiento
import http.server
import socketserver
import json
import os
import re
import unicodedata
from respuestas_chatbot import ObtenerRespuesta  # Función personalizada para obtener la respuesta del bot
import locale

# Establecer configuración regional en español (para fechas u otros datos localizados)
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    print("La configuración regional 'es_ES.UTF-8' no está disponible.")

# Cargar archivo de intenciones en formato JSON
try:
    with open('Informacion.json', 'r', encoding='utf-8') as archivo:
        Intentos = json.load(archivo)
except Exception as e:
    print(f"❌ Error cargando 'Informacion.json': {e}")
    Intentos = {}

# ----------------------- FUNCIONES DE PROCESAMIENTO DE TEXTO -----------------------

# Función para normalizar texto: elimina acentos y convierte a minúsculas
def NormalizarTexto(Texto):
    Texto = Texto.lower()
    return ''.join(c for c in unicodedata.normalize('NFKD', Texto) if unicodedata.category(c) != 'Mn')

# Tokeniza una oración en palabras
def Tokenizar(oracion):
    oracion = NormalizarTexto(oracion)
    return re.findall(r'\b\w+\b', oracion)

# Genera todos los n-gramas (hasta n=4) posibles a partir de los tokens
def GenerarNGramas(tokens, max_n=4):
    ngramas = set()
    longitud = len(tokens)
    for n in range(1, max_n + 1):
        for i in range(longitud - n + 1):
            ngrama = " ".join(tokens[i:i + n])
            ngramas.add(ngrama)
    return ngramas

# Busca coincidencias exactas entre n-gramas del input y las frases de ejemplo en el archivo JSON
def BuscarConNGramas(oracion, intentos_json):
    tokens = Tokenizar(oracion)
    ngramas = GenerarNGramas(tokens)

    for intento in intentos_json["intents"]:
        for frase in intento["preguntas"]:
            frase_normalizada = NormalizarTexto(frase)
            if frase_normalizada in ngramas:
                return [{"Intencion": intento["tag"], "Probabilidad": "1.0"}]

    return [{"Intencion": "unknown", "Probabilidad": "0.0"}]

# ----------------------- CONFIGURACIÓN DEL SERVIDOR HTTP -----------------------

PUERTO = 8000

class ManejadorChatbot(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        if os.path.exists(self.path[1:]):
            return super().do_GET()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Archivo no encontrado')

    def do_POST(self):
        try:
            longitud = int(self.headers.get('Content-Length', 0))
            datos_post = self.rfile.read(longitud)
            datos = json.loads(datos_post.decode('utf-8'))
            pregunta = datos.get('prompt', '').strip()

            if not pregunta:
                respuesta = {"response": ["Por favor, ingresa un mensaje o pregunta."]}
            else:
                intentos = BuscarConNGramas(pregunta, Intentos)
                if intentos and intentos[0]['Intencion'] == 'unknown':
                    intentos[0]['TextoUsuario'] = pregunta
                texto_respuesta = ObtenerRespuesta(intentos, Intentos)
                respuesta = {"response": texto_respuesta}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(respuesta, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8'))

# ----------------------- INICIAR SERVIDOR -----------------------

with socketserver.ThreadingTCPServer(('0.0.0.0', PUERTO), ManejadorChatbot) as httpd:
    print(f'Servidor ejecutándose en: http://localhost:{PUERTO}/')
    httpd.serve_forever()
