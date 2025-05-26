# verificar_share.py
from pathlib import Path

EXP_ROOT = Path("/data/expedientes")  # punto de montaje del share

def listar_contenido():
    for año in ["2025"]:  # podés agregar otros años si querés
        path_año = EXP_ROOT / año
        if not path_año.exists():
            print(f"❌ No existe: {path_año}")
            continue
        for letra in path_año.iterdir():
            if letra.is_dir():
                print(f"\n📁 {letra.name}/")
                for expediente in sorted(letra.iterdir()):
                    if expediente.is_dir():
                        pdf = expediente / f"{expediente.name}.pdf"
                        if pdf.exists():
                            print(f"  ✅ {pdf.name}")
                        else:
                            print(f"  ❌ Falta PDF: {pdf}")

if __name__ == "__main__":
    listar_contenido()
