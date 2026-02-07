"""Script rápido para testar o endpoint de perfil e capturar erros."""
import urllib.request
import urllib.error

url = "http://localhost:8001/api/perfil/kpis?dimensao=procurador&valor=Kaoye+Guazina+Oshiro"
try:
    r = urllib.request.urlopen(url)
    print(r.read().decode())
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(e.read().decode())
