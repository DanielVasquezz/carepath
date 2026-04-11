import os

def generate_report():
    # Archivos que queremos inspeccionar (los más importantes)
    target_files = [
        "src/main.py",
        "src/core/config.py",
        "src/core/security.py",
        "src/core/database.py",
        "src/models/db/patient_db.py",
        "src/api/v1/endpoints/auth.py",
        ".env" # Cuidado: el reporte mostrará tus keys si las tienes aquí
    ]
    
    report = []
    report.append("=== CAREPATH PROJECT STRUCTURE ===")
    
    # 1. Mapear el árbol de directorios (limitado a 3 niveles)
    for root, dirs, files in os.walk("."):
        if "env" in root or "__pycache__" in root or ".git" in root:
            continue
        level = root.replace(".", "").count(os.sep)
        indent = " " * 4 * level
        report.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 4 * (level + 1)
        for f in files:
            if not f.endswith(".pyc"):
                report.append(f"{sub_indent}{f}")

    report.append("\n=== KEY FILE CONTENTS ===")
    
    # 2. Leer contenido de archivos clave
    for file_path in target_files:
        if os.path.exists(file_path):
            report.append(f"\n--- FILE: {file_path} ---")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    report.append(content)
            except Exception as e:
                report.append(f"Could not read file: {e}")
        else:
            report.append(f"\n--- FILE: {file_path} (NOT FOUND) ---")

    # Guardar reporte
    with open("project_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    print("✅ Reporte generado con éxito en: project_report.txt")

if __name__ == "__main__":
    generate_report()