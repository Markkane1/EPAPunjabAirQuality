import copy
from fastapi.testclient import TestClient
from src.api.main import app
from src.domain.entities.models import DistrictObservation

client = TestClient(app)

# 1. Verify GET /api/v1/meta/districts
res = client.get('/api/v1/meta/districts')
assert res.status_code == 200
data = res.json()
assert len(data) == 41
print(f'Endpoint /api/v1/meta/districts: {len(data)} districts returned dynamically.')

# 2. Verify GET /api/v1/meta/stations
res = client.get('/api/v1/meta/stations')
assert res.status_code == 200
stations = res.json()
assert len(stations) == 85
print(f'Endpoint /api/v1/meta/stations: {len(stations)} stations returned dynamically.')

# 3. Verify GET /api/v1/observations/current
res = client.get('/api/v1/observations/current?pollutant=AQI')
assert res.status_code == 200
curr = res.json()
assert 'districts' in curr and 'airports' in curr and 'provincial_summary' in curr
assert len(curr['districts']) == 41
initial_lahore_aqi = curr['districts']['Lahore']['aqi']
initial_mean_aqi = curr['provincial_summary']['mean_aqi']
print(f"Endpoint /api/v1/observations/current: initial Lahore AQI={initial_lahore_aqi}, initial mean_aqi={initial_mean_aqi}")

# 4. Mutate observation in repository and verify /current reflects the mutation dynamically!
repo = app.state.repo
latest_dt = repo.get_latest_timestamp()
orig_obs = repo.get_district_observation('Lahore', latest_dt)
assert orig_obs is not None

# Mutate Lahore AQI to 499
mutated_obs = copy.replace(orig_obs, aqi=499, pm25=499.0)
repo.add_district_observation(mutated_obs)

res2 = client.get('/api/v1/observations/current?pollutant=AQI')
assert res2.status_code == 200
curr2 = res2.json()
lahore_reading = curr2['districts']['Lahore']
assert lahore_reading['aqi'] == 499, f"Expected 499, got {lahore_reading['aqi']}"
new_mean_aqi = curr2['provincial_summary']['mean_aqi']
assert new_mean_aqi > initial_mean_aqi, f"Expected mean_aqi to increase, got {new_mean_aqi} vs {initial_mean_aqi}"
print(f"Dynamic mutation confirmed! Lahore AQI updated {initial_lahore_aqi} -> {lahore_reading['aqi']}, mean_aqi updated {initial_mean_aqi} -> {new_mean_aqi}")

# 5. Test Physical Domain Guard on /api/v1/analytics/flux
flux_bad = client.get('/api/v1/analytics/flux?pollutant=AQI')
assert flux_bad.status_code == 400
assert 'dimensionless' in flux_bad.json()['detail'].lower()
print('Physical domain guard verified: AQI on /flux correctly rejected with HTTP 400.')

# 6. Test valid flux
flux_ok = client.get('/api/v1/analytics/flux?pollutant=PM2.5')
assert flux_ok.status_code == 200
flux_data = flux_ok.json()
assert 'top_pathways' in flux_data
print(f"Endpoint /api/v1/analytics/flux: {len(flux_data['top_pathways'])} pathways computed.")

# 7. Test /api/v1/spatial/surface
surf_res = client.get('/api/v1/spatial/surface?pollutant=PM2.5&resolution=20')
assert surf_res.status_code == 200
surf_data = surf_res.json()
assert len(surf_data['grid_matrix']) > 0
print(f"Endpoint /api/v1/spatial/surface: grid shape=({len(surf_data['grid_matrix'])}, {len(surf_data['grid_matrix'][0])}) interpolated.")

print('ALL API DYNAMIC TRACING PROBES PASSED CLEANLY!')
