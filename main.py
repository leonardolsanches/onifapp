from flask import Flask, render_template
from onvif import ONVIFCamera
from zeep import Client
import threading
import time
import os

app = Flask(__name__)

# Configuração da câmera
CAMERA_IP = "192.168.0.4"
CAMERA_PORT = 8899
CAMERA_USER = "admin"
CAMERA_PASS = "admin"
PRESET_PADRAO = "1"
WSDL_DIR = os.path.join(os.path.dirname(__file__), "wsdl")

# Inicializar câmera ONVIF
try:
    cam = ONVIFCamera(CAMERA_IP, CAMERA_PORT, CAMERA_USER, CAMERA_PASS, WSDL_DIR)
    media = cam.create_media_service()
    ptz = cam.create_ptz_service()
    # Obter o primeiro perfil de mídia
    perfis = media.GetProfiles()
    perfil_midia = perfis[0]
except Exception as e:
    print(f"Falha ao inicializar a câmera: {e}")
    exit(1)

def ir_para_preset(preset_token):
    """Mover a câmera para o preset especificado."""
    try:
        requisicao = ptz.create_type("GotoPreset")
        requisicao.ProfileToken = perfil_midia.token
        requisicao.PresetToken = preset_token
        ptz.GotoPreset(requisicao)
        return True
    except Exception as e:
        print(f"Erro ao mover para o preset {preset_token}: {e}")
        return False

def obter_status_ptz():
    """Obter o status PTZ atual."""
    try:
        requisicao = ptz.create_type("GetStatus")
        requisicao.ProfileToken = perfil_midia.token
        status = ptz.GetStatus(requisicao)
        return status
    except Exception as e:
        print(f"Erro ao obter status PTZ: {e}")
        return None

def watchdog():
    """Monitorar a posição da câmera e retornar ao preset padrão se necessário."""
    while True:
        try:
            status = obter_status_ptz()
            if status and status.Position:
                pan_tilt = status.Position.PanTilt
                # Verificar se a posição desviou do esperado (assumindo que preset 1 está em x=1.0, y=1.0)
                if abs(pan_tilt.x - 1.0) > 0.01 or abs(pan_tilt.y - 1.0) > 0.01:
                    print(f"Desvio de posição detectado (x={pan_tilt.x}, y={pan_tilt.y}). Retornando ao preset {PRESET_PADRAO}.")
                    ir_para_preset(PRESET_PADRAO)
            else:
                print("Falha ao recuperar o status PTZ.")
        except Exception as e:
            print(f"Erro no watchdog: {e}")
        time.sleep(10)  # Verificar a cada 10 segundos

# Iniciar thread watchdog
watchdog_thread = threading.Thread(target=watchdog, daemon=True)
watchdog_thread.start()

@app.route("/")
def index():
    """Renderizar a interface principal."""
    return render_template("index.html")

@app.route("/preset/<id>")
def definir_preset(id):
    """Mover a câmera para o preset especificado."""
    if id in ["1", "2", "3"]:
        sucesso = ir_para_preset(id)
        if sucesso:
            return f"Movido para o preset {id}"
        else:
            return f"Falha ao mover para o preset {id}", 500
    return "ID de preset inválido", 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
