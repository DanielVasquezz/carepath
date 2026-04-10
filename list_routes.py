from src.main import app

def list_endpoints():
    print(f"{'METODO':<10} | {'RUTA':<40} | {'NOMBRE'}")
    print("-" * 70)
    for route in app.routes:
        # Extraemos los métodos (GET, POST, etc.)
        methods = ", ".join(getattr(route, "methods", ["N/A"]))
        # La ruta y el nombre de la función encargada
        path = route.path
        name = getattr(route, "name", "N/A")
        
        print(f"{methods:<10} | {path:<40} | {name}")

if __name__ == "__main__":
    list_endpoints()