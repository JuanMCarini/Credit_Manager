import requests

res = requests.get('http://127.0.0.1:8000/api/v1/reports/balances?agrupar=true&agrupadores=clientes&agrupadores=credito')
print("Status Code:", res.status_code)

try:
    data = res.json()
    print("Rows:", len(data))
    if len(data) > 0:
        print("First row keys:", list(data[0].keys()))
except Exception as e:
    print("Error:", e)
