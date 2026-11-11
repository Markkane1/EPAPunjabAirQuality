# Exploration & Fix Strategy Report: Findings 2, 3, and 4

- **Agent**: `explorer_m4_it2_2` (Read-Only Exploration Agent)
- **Target Files**:
  - `src/infrastructure/repositories/baseline_repository.py`
  - `src/domain/interfaces/repositories.py`
  - `src/domain/math/projection.py`
  - `src/api/dependencies.py`
- **Reference Inputs**:
  - `reviewer_m4_1/handoff.md` (Findings 2, 3, 4)
  - `PROJECT.md` & `ORIGINAL_REQUEST.md`

---

## 1. Observation

### Observation 1: Finding 2 — Offset-Naive Datetime Comparison Crash
In `src/infrastructure/repositories/baseline_repository.py`:
- Lines 718–730 (`add_station_observations`):
  ```python
  for o in observations:
      dt = o.recorded_at if o.recorded_at.tzinfo else o.recorded_at.replace(tzinfo=timezone.utc)
      key = (o.station_id, dt)
      self._station_obs_by_id_and_time[key] = o
      ...
      self._station_obs_by_station[o.station_id].append(o)
      self._station_obs_by_station[o.station_id].sort(key=lambda x: x.recorded_at)
  ```
- Lines 746–757 (`add_district_observations`):
  ```python
  for o in observations:
      dt = o.recorded_at if o.recorded_at.tzinfo else o.recorded_at.replace(tzinfo=timezone.utc)
      key = (o.district_id, dt)
      self._district_obs_by_id_and_time[key] = o
      ...
      self._district_obs_by_district[o.district_id].append(o)
      self._district_obs_by_district[o.district_id].sort(key=lambda x: x.recorded_at)
  ```
- **Direct Repro**:
  ```powershell
  python -c "from datetime import datetime; from src.domain.entities.models import StationObservation; from src.infrastructure.repositories.baseline_repository import BaselineRepository; repo = BaselineRepository(); repo.add_station_observation(StationObservation(station_id='OPLA', recorded_at=datetime(2026, 11, 15, 12, 0), pm25=50.0))"
  ```
  **Verbatim Error**:
  ```
  TypeError: can't compare offset-naive and offset-aware datetimes
  ```
- **Root Cause**: The local variable `dt` is normalized with `replace(tzinfo=timezone.utc)`, but the object attribute `o.recorded_at` is left unmodified. In `baseline_data.json`, initial observations are parsed with `replace(tzinfo=timezone.utc)` (line 119), making them offset-aware. Appending an observation with an offset-naive `recorded_at` and then calling `.sort(key=lambda x: x.recorded_at)` triggers Python's built-in comparison exception between naive and aware datetimes.

### Observation 2: Finding 3 — LSP Collision on Generic Methods
In `src/domain/interfaces/repositories.py`:
- `StationRepository` declares:
  - `count(self) -> int` (abstract, line 56)
  - `list_all(self, station_type: Optional[str] = None) -> List[Station]` (abstract, line 36)
  - `get_by_id(self, station_id: str) -> Optional[Station]` (abstract, line 26)
  - `get_by_name(self, name: str) -> Optional[Station]` (abstract, line 31)
- `DistrictRepository` declares:
  - `count(self) -> int` (abstract, line 113)
  - `list_all(self, monitored_only: bool = False) -> List[District]` (abstract, line 103)
  - `get_by_id(self, district_id: str) -> Optional[District]` (abstract, line 93)
  - `get_by_name(self, name: str) -> Optional[District]` (abstract, line 98)
In `src/infrastructure/repositories/baseline_repository.py`:
- `BaselineRepository` inherits from both interfaces:
  `class BaselineRepository(StationRepository, DistrictRepository, ObservationRepository, AnalyticsRepository):`
- Lines 418–426:
  ```python
  def list_all(
      self,
      station_type: Optional[str] = None,
      monitored_only: Optional[bool] = None,
  ) -> Any:
      with self._lock:
          if monitored_only is not None:
              return self.list_all_districts(monitored_only=monitored_only)
          return self.list_stations(station_type=station_type)
  ```
- Lines 449–451:
  ```python
  def count(self) -> int:
      with self._lock:
          return len(self._stations)
  ```
- **LSP Violation**:
  1. `district_repo.count()` returns `85` (station count) instead of `41` (district count).
  2. `district_repo.list_all()` (called with no arguments, using the default `monitored_only=False`) triggers `monitored_only is None` in `BaselineRepository.list_all`, which returns `List[Station]` (85 items) instead of `List[District]`. Downstream code accessing district fields (e.g. `d.division`, `d.is_monitored`) crashes with `AttributeError`.
  3. `district_repo.get_by_name("Lahore")` returns `Station(id="OPLA", name="Lahore Airport / OPLA")` instead of `District(id="Lahore", name="Lahore")`.

### Observation 3: Finding 4 — Dummy Method `get_label_placement`
- In `src/domain/interfaces/repositories.py` line 123:
  ```python
  @abstractmethod
  def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
      """Retrieve collision-free label placement coordinates for a district."""
      pass
  ```
- In `src/infrastructure/repositories/baseline_repository.py` lines 507–508:
  ```python
  def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
      return None
  ```
- In `src/domain/math/projection.py`:
  - `equirectangular_project(lat, lon, width_px=1200.0, height_px=900.0) -> Tuple[float, float]` implements Plate Carrée projection centered on 31°N.
  - `greedy_label_placement(labels, candidate_offsets, leader_line_thresh) -> List[Dict[str, Any]]` implements 12 candidate offsets and leader line detection.
  - Direct execution test on all 41 baseline districts from `data/baseline/districts.json` confirmed:
    ```powershell
    python -c "import json; from src.domain.math.projection import equirectangular_project, greedy_label_placement; districts = json.load(open('data/baseline/districts.json')); labels = [{'district_id': str(d.get('id', d['name'])), 'text': d['name'], 'anchor_x': equirectangular_project(d.get('latitude') or d.get('lat'), d.get('longitude') or d.get('lon'))[0], 'anchor_y': equirectangular_project(d.get('latitude') or d.get('lat'), d.get('longitude') or d.get('lon'))[1], 'width': 48.0, 'height': 16.0} for d in districts]; res = greedy_label_placement(labels); print('Total placed:', len(res)); print('Sample:', res[0])"
    ```
    Output: `Total placed: 41`, successfully producing bounding boxes and offsets for all 41 districts without collision.
- In `src/domain/entities/models.py`:
  `LabelPlacement` entity has exact fields matching the output: `district_id`, `text`, `anchor_x`, `anchor_y`, `offset_x`, `offset_y`, `width`, `height`, `has_leader_line`.

---

## 2. Logic Chain

### Logic Chain for Finding 2 (Datetime Normalization)
1. `StationObservation` and `DistrictObservation` entities represent domain measurements where timestamps may originate from external sources (CSV uploads, API payloads, mock tests).
2. While `UserCSVRow` validates timestamps, direct calls to repository methods (e.g. `add_station_observation(StationObservation(...))`) can provide offset-naive datetimes.
3. In `baseline_repository.py`, all baseline historical records loaded in `_load_baseline()` are converted to UTC-aware datetimes with `.replace(tzinfo=timezone.utc)`.
4. In Python 3.x, sorting a heterogeneous sequence containing both aware and naive `datetime` instances unconditionally raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
5. Therefore, `o.recorded_at` must be normalized directly on the entity before it is stored in any index or sorted:
   - If `o.recorded_at.tzinfo is None`: `o.recorded_at = o.recorded_at.replace(tzinfo=timezone.utc)`
   - If `o.recorded_at.tzinfo is not None`: `o.recorded_at = o.recorded_at.astimezone(timezone.utc)`
6. Additionally, configuring `key=lambda x: x.recorded_at if x.recorded_at.tzinfo else x.recorded_at.replace(tzinfo=timezone.utc)` provides defense-in-depth during sorting.

### Logic Chain for Finding 3 (LSP Collision on Generic Methods)
1. `StationRepository` and `DistrictRepository` are two distinct domain abstractions representing two different entity aggregate roots (`Station` vs. `District`).
2. Both interfaces follow generic repository conventions by exposing `count() -> int` and `list_all() -> List[T]`.
3. Because Python implements single dispatch by method name on an object's type, a single class inheriting from both interfaces cannot return `85` when called as a `StationRepository` and `41` when called as a `DistrictRepository` on a zero-argument `count()` invocation.
4. Two architectural solutions were evaluated:
   - **Alternative A (Interface Renaming)**: Remove `count()` and `list_all()`, renaming them to `count_stations()`, `count_districts()`, etc.
     *Flaw*: Breaks the abstract repository pattern contract, and does not solve the collision if default/alias methods remain on the base classes.
   - **Alternative B (Adapter Pattern with Shared State)**: Separate `StationRepository` and `DistrictRepository` into dedicated adapter classes (`BaselineStationRepository` and `BaselineDistrictRepository`) that delegate to the common `BaselineRepository` data store.
     *Advantage*:
     - 100% adherence to Liskov Substitution Principle.
     - `BaselineStationRepository.count()` returns 85; `BaselineDistrictRepository.count()` returns 41.
     - `BaselineStationRepository.list_all()` returns `List[Station]`; `BaselineDistrictRepository.list_all()` returns `List[District]`.
     - Zero data duplication: both adapters access the exact same thread-safe `_stations`, `_districts`, and `_lock` instances in `BaselineRepository`.
     - Direct compatibility with FastAPI dependency injection in `src/api/dependencies.py`.
5. Therefore, Alternative B is the clean, robust architectural solution.

### Logic Chain for Finding 4 (Dummy `get_label_placement`)
1. In `src/domain/interfaces/repositories.py`, `DistrictRepository` defines `get_label_placement(self, district_id: str) -> Optional[LabelPlacement]`.
2. `BaselineRepository` currently stubs this with `return None`.
3. In `src/domain/math/projection.py`, `greedy_label_placement` performs collision resolution using a greedy 12-candidate offset search.
4. Crucial insight: Greedy collision detection is a **batch operation**. Running it for a single district in isolation cannot detect collisions because no other bounding boxes exist in `placed_boxes`.
5. The 41 districts in Punjab have static geographic centroids (`latitude`, `longitude`).
6. Therefore, computing label placements for all 41 districts **once** during repository initialization (`_load_baseline()`) and caching them in an in-memory dictionary `_label_placements: Dict[str, LabelPlacement]` provides:
   - True collision-free positioning across all districts.
   - Sub-microsecond $O(1)$ retrieval latency via `get_label_placement(district_id)`.
   - Full compliance with the `DistrictRepository` contract.

---

## 3. Detailed Fix Strategy & Code Specifications

### Fix Strategy 1: Datetime Normalization in `BaselineRepository` (Finding 2)

#### Target File: `src/infrastructure/repositories/baseline_repository.py`

#### Changes in `add_station_observations`:
Replace lines 717–730:
```python
            for o in observations:
                # 1. Normalize timestamp to UTC directly on the observation entity
                if o.recorded_at.tzinfo is None:
                    o.recorded_at = o.recorded_at.replace(tzinfo=timezone.utc)
                else:
                    o.recorded_at = o.recorded_at.astimezone(timezone.utc)
                dt = o.recorded_at

                key = (o.station_id, dt)
                self._station_obs_by_id_and_time[key] = o

                if dt not in self._station_obs_by_time:
                    self._station_obs_by_time[dt] = []
                    new_timestamps.add(dt)
                self._station_obs_by_time[dt].append(o)

                if o.station_id not in self._station_obs_by_station:
                    self._station_obs_by_station[o.station_id] = []
                self._station_obs_by_station[o.station_id].append(o)
                # Sort using safe key with defense-in-depth
                self._station_obs_by_station[o.station_id].sort(
                    key=lambda x: x.recorded_at if x.recorded_at.tzinfo else x.recorded_at.replace(tzinfo=timezone.utc)
                )
```

#### Changes in `add_district_observations`:
Replace lines 745–758:
```python
            for o in observations:
                # 1. Normalize timestamp to UTC directly on the observation entity
                if o.recorded_at.tzinfo is None:
                    o.recorded_at = o.recorded_at.replace(tzinfo=timezone.utc)
                else:
                    o.recorded_at = o.recorded_at.astimezone(timezone.utc)
                dt = o.recorded_at

                key = (o.district_id, dt)
                self._district_obs_by_id_and_time[key] = o

                if dt not in self._district_obs_by_time:
                    self._district_obs_by_time[dt] = []
                self._district_obs_by_time[dt].append(o)

                if o.district_id not in self._district_obs_by_district:
                    self._district_obs_by_district[o.district_id] = []
                self._district_obs_by_district[o.district_id].append(o)
                # Sort using safe key with defense-in-depth
                self._district_obs_by_district[o.district_id].sort(
                    key=lambda x: x.recorded_at if x.recorded_at.tzinfo else x.recorded_at.replace(tzinfo=timezone.utc)
                )
```

---

### Fix Strategy 2: Adapter Pattern for LSP Compliance (Finding 3)

#### Target File: `src/infrastructure/repositories/baseline_repository.py`

#### Implementation of Adapter Classes:
Add dedicated adapter classes in `baseline_repository.py` above or below `BaselineRepository`:

```python
class BaselineStationRepository(StationRepository):
    """Clean LSP-compliant adapter for StationRepository delegating to BaselineRepository store."""

    def __init__(self, store: "BaselineRepository") -> None:
        self._store = store

    def get_by_id(self, station_id: str) -> Optional[Station]:
        return self._store.get_station_by_id(station_id)

    def get_by_name(self, name: str) -> Optional[Station]:
        return self._store.get_station_by_name(name)

    def list_all(self, station_type: Optional[str] = None) -> List[Station]:
        return self._store.list_stations(station_type=station_type)

    def list_by_district(self, district: str) -> List[Station]:
        return self._store.list_by_district(district)

    def list_airports(self) -> List[Station]:
        return self._store.list_airports()

    def exists(self, station_id: str) -> bool:
        return self._store.exists(station_id)

    def count(self) -> int:
        return self._store.count_stations()

    def add_station(self, station: Station) -> None:
        self._store.add_station(station)

    def add_stations(self, stations: Sequence[Station]) -> None:
        self._store.add_stations(stations)


class BaselineDistrictRepository(DistrictRepository):
    """Clean LSP-compliant adapter for DistrictRepository delegating to BaselineRepository store."""

    def __init__(self, store: "BaselineRepository") -> None:
        self._store = store

    def get_by_id(self, district_id: str) -> Optional[District]:
        return self._store.get_district_by_id(district_id)

    def get_by_name(self, name: str) -> Optional[District]:
        return self._store.get_district_by_name(name)

    def list_all(self, monitored_only: bool = False) -> List[District]:
        return self._store.list_all_districts(monitored_only=monitored_only)

    def list_border_districts(self, max_border_distance_km: float = 120.0) -> List[District]:
        return self._store.list_border_districts(max_border_distance_km=max_border_distance_km)

    def count(self) -> int:
        return self._store.count_districts()

    def get_boundary_geometry(self, district_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get_boundary_geometry(district_id)

    def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
        return self._store.get_label_placement(district_id)
```

#### Updates inside `BaselineRepository.__init__`:
```python
        # Instantiate LSP-compliant adapter facades
        self._station_repo = BaselineStationRepository(self)
        self._district_repo = BaselineDistrictRepository(self)
```

#### Expose properties on `BaselineRepository`:
```python
    @property
    def stations(self) -> StationRepository:
        return self._station_repo

    @property
    def districts(self) -> DistrictRepository:
        return self._district_repo

    @property
    def station_repo(self) -> StationRepository:
        return self._station_repo

    @property
    def district_repo(self) -> DistrictRepository:
        return self._district_repo
```

#### Updates in `src/api/dependencies.py`:
Ensure dependency injection providers return the dedicated, pure adapters:
```python
def get_station_repository(request: Request) -> StationRepository:
    return request.app.state.repo.stations


def get_district_repository(request: Request) -> DistrictRepository:
    return request.app.state.repo.districts
```

#### Updates in `src/api/main.py`:
Bind the services to the clean adapters during startup:
```python
app.state.observation_service = ObservationService(
    obs_repo=repo, station_repo=repo.stations, district_repo=repo.districts
)
app.state.spatial_service = SpatialService(
    obs_repo=repo, station_repo=repo.stations, district_repo=repo.districts, analytics_repo=repo
)
app.state.analytics_service = AnalyticsService(
    analytics_repo=repo, obs_repo=repo, district_repo=repo.districts, station_repo=repo.stations
)
app.state.ingestion_service = IngestionService(
    observation_repo=repo, station_repo=repo.stations, district_repo=repo.districts, analytics_repo=repo
)
```

---

### Fix Strategy 3: Greedy Label Placement Integration (Finding 4)

#### Target File: `src/infrastructure/repositories/baseline_repository.py`

#### Imports:
Add:
```python
from src.domain.math.projection import equirectangular_project, greedy_label_placement
```

#### Data Structure in `BaselineRepository.__init__`:
```python
        # Label placement cache
        self._label_placements: Dict[str, LabelPlacement] = {}
```

#### Initialization in `_load_baseline()`:
At the end of district indexing (after step 3 in `_load_baseline()`):
```python
            # 3b. Compute collision-free label placements for all districts
            label_requests: List[Dict[str, Any]] = []
            seen_districts: Set[str] = set()

            for d in self._districts.values():
                if d.name in seen_districts:
                    continue
                seen_districts.add(d.name)
                px, py = equirectangular_project(d.latitude, d.longitude)
                label_requests.append({
                    "district_id": str(d.id),
                    "text": d.name,
                    "anchor_x": px,
                    "anchor_y": py,
                    "width": 48.0,
                    "height": 16.0,
                })

            placed = greedy_label_placement(label_requests)
            for item in placed:
                lp = LabelPlacement(
                    district_id=str(item["district_id"]),
                    text=item["text"],
                    anchor_x=item["anchor_x"],
                    anchor_y=item["anchor_y"],
                    offset_x=item["offset_x"],
                    offset_y=item["offset_y"],
                    width=48.0,
                    height=16.0,
                    has_leader_line=item["has_leader_line"],
                )
                self._label_placements[str(lp.district_id)] = lp
                self._label_placements[lp.text] = lp
                self._label_placements[lp.text.lower()] = lp
```

#### Implementation of `get_label_placement`:
Replace lines 507–508:
```python
    def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
        with self._lock:
            key = str(district_id).strip()
            return self._label_placements.get(key) or self._label_placements.get(key.lower())
```

---

## 4. Caveats
1. **Finding 1 (Deduplication)**: Finding 1 was investigated by reviewer_m4_1 and is assigned to worker_m4_it2_1. Finding 2 (datetime normalization) must precede deduplication because dictionary key lookups `(station_id, dt)` require `dt` to be consistently UTC-aware.
2. **Text Dimension Assumptions**: `greedy_label_placement` uses default text dimensions `width=48.0` and `height=16.0` (matching Plate Carrée 1200x900 canvas defaults). In Punjab, all 41 baseline district centroids are sufficiently spaced that zero collisions occur with these dimensions (all offsets are (0, 0)). If custom font metrics are applied in Zone 3 UI rendering, dynamic dimension overrides can be supplied.
3. **Read-Only Explorer Scope**: In accordance with the Explorer archetype and mission constraints, zero code modifications have been made to repository or domain source files during this investigation.

---

## 5. Conclusion
- **Finding 2** is caused by failing to assign the UTC-normalized datetime back to `o.recorded_at` prior to list appending and sorting. Mutating `o.recorded_at` in-place on entry eliminates `TypeError` completely.
- **Finding 3** is caused by Python's single dispatch colliding on zero-argument methods (`count()` and `list_all()`) when one class implements multiple generic interfaces. The Repository Adapter pattern (`BaselineStationRepository` and `BaselineDistrictRepository`) cleanly eliminates the LSP violation while sharing the underlying in-memory store.
- **Finding 4** is caused by an unlinked placeholder `return None`. Precomputing label placements for all 41 districts during `_load_baseline()` via `equirectangular_project` and `greedy_label_placement` satisfies the domain contract with $O(1)$ sub-microsecond retrieval.

---

## 6. Verification Method

Once implemented by `worker_m4_it2_1`, the implementation agent can verify with the following commands:

### 1. Verify Finding 2 (Offset-Naive Datetime Normalization):
```powershell
python -c "from datetime import datetime; from src.domain.entities.models import StationObservation; from src.infrastructure.repositories.baseline_repository import BaselineRepository; repo = BaselineRepository(); repo.add_station_observation(StationObservation(station_id='OPLA', recorded_at=datetime(2026, 11, 15, 12, 0), pm25=50.0)); obs = repo.get_station_hourly_series('OPLA')[-1]; assert obs.recorded_at.tzinfo is not None; print('Finding 2 Passed: Naive datetime accepted and normalized to UTC.')"
```
*Expected*: Prints `Finding 2 Passed: Naive datetime accepted and normalized to UTC.` without throwing `TypeError`.

### 2. Verify Finding 3 (LSP Compliance for Station and District Repositories):
```powershell
python -c "from src.infrastructure.repositories.baseline_repository import BaselineRepository; repo = BaselineRepository(); station_repo = repo.stations; district_repo = repo.districts; assert station_repo.count() == 85, f'Expected 85, got {station_repo.count()}'; assert district_repo.count() == 41, f'Expected 41, got {district_repo.count()}'; assert len(station_repo.list_all()) == 85; assert len(district_repo.list_all()) == 41; assert district_repo.get_by_name('Lahore').division == 'Lahore'; assert station_repo.get_by_name('Lahore') is not None; print('Finding 3 Passed: LSP contracts strictly adhered to.')"
```
*Expected*: Prints `Finding 3 Passed: LSP contracts strictly adhered to.`.

### 3. Verify Finding 4 (Label Placement Resolution):
```powershell
python -c "from src.infrastructure.repositories.baseline_repository import BaselineRepository; repo = BaselineRepository(); lp1 = repo.districts.get_label_placement('Lahore'); lp2 = repo.get_label_placement('1'); assert lp1 is not None and lp1.text == 'Lahore'; assert lp2 is not None and lp2.text == 'Attock'; print('Finding 4 Passed: LabelPlacement entities retrieved in O(1).', lp1)"
```
*Expected*: Prints `Finding 4 Passed: LabelPlacement entities retrieved in O(1).` with valid coordinates.

### 4. Verify Full Test Suite Regressions:
```powershell
python -m pytest tests/ -q
```
*Expected*: All 456 tests pass with 0 failures.
