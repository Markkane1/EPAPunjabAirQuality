import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
res = client.get('/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5')
print('Status:', res.status_code)
if res.status_code == 200:
    data = res.json()
    print('District:', data.get('district'))
    print('Threshold P75:', data.get('threshold_p75'))
    print('Calm fraction:', data.get('calm_fraction'))
    for s in data.get('sectors', []):
        sec_idx = s['sector_index']
        lbl = s['direction_label']
        az = s['azimuth_deg']
        n = s['total_hours']
        m = s['exceedance_hours']
        prob = s['cpf_probability']
        print(f"Sector {sec_idx} ({lbl}, az={az}): N={n}, m={m}, prob={prob}")
else:
    print('Response:', res.text)
