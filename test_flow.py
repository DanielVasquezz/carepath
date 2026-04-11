import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_full_carepath_flow():
    print("\n🚀 --- INICIANDO TEST INTEGRAL CAREPATH --- 🚀")
    
    # 1. LOGIN
    print("\n🔐 [1/4] Autenticando usuario...")
    login_data = {
        "username": "daniel@mora.sv",
        "password": "password123"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=login_data)
        response.raise_for_status()
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Autenticación exitosa.")
    except Exception as e:
        print(f"❌ Error en Login: {e}")
        return

    # 2. CREAR CASO
    print("\n🏥 [2/4] Registrando nuevo caso de emergencia...")
    case_payload = {
        "chief_complaint": "Dolor de pecho agudo y dificultad para respirar",
        "symptoms": [
            {
                "description": "Presión intensa en el esternón",
                "severity": "high",
                "duration_hours": 1,
                "body_location": "Tórax",
                "is_worsening": True
            }
        ]
    }
    case_res = requests.post(f"{BASE_URL}/api/v1/cases/", json=case_payload, headers=headers)
    case_id = case_res.json()["id"]
    print(f"✅ Caso creado con ID: {case_id}")

    # 3. EVALUAR (Aquí es donde probamos el fix del UUID y la IA)
    print("\n🧠 [3/4] Ejecutando evaluación lógica + IA...")
    print("   (Esto puede tardar unos segundos por Ollama...)")
    
    eval_res = requests.post(f"{BASE_URL}/api/v1/cases/{case_id}/evaluate", headers=headers)
    
    if eval_res.status_code == 200:
        data = eval_res.json()
        print(f"✅ Evaluación completada!")
        print(f"📊 PRIORIDAD: {data['priority']}")
        print(f"🤖 RECOMENDACIÓN:\n{data['ai_recommendation'][:200]}...")
    else:
        print(f"❌ Error en Evaluación: {eval_res.status_code}")
        print(f"Detalle: {eval_res.text}")
        return

    # 4. VERIFICAR GET
    print("\n💾 [4/4] Verificando persistencia en base de datos...")
    final_res = requests.get(f"{BASE_URL}/api/v1/cases/{case_id}", headers=headers)
    if final_res.status_code == 200:
        print("✨ PRUEBA FINALIZADA: Todo el sistema está conectado y funcionando.")
    else:
        print("⚠️ No se pudo recuperar el caso final.")

if __name__ == "__main__":
    test_full_carepath_flow()