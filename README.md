# 3D Ultimator

Offline cargo-space planner for Windows, with automatic 3D packing and manual placement.
Interfejs w języku polskim i angielskim / Polish and English interface.

## Pobieranie / Download

Gotowy program znajduje się w [Releases](https://github.com/hudzialke/3DUltimator/releases/latest):

- **Setup EXE** — instalator Windows x64, z wyborem języka polskiego i angielskiego.
- **Portable ZIP** — rozpakuj cały plik ZIP i uruchom `3DUltimator.exe`.
- Python nie jest potrzebny do uruchamiania gotowego programu.
- Folder `_internal` musi pozostać obok `3DUltimator.exe`.
- Instalator działa dla bieżącego użytkownika, bez uprawnień administratora.

Download the **Setup EXE** to install, or extract the entire **portable ZIP** and run
`3DUltimator.exe`. Keep `_internal` beside the executable. Python is not required.
The installer supports Polish and English and installs for the current user without administrator privileges.

## Obsługa

- Wybierz **Polski / English** w prawym górnym rogu. Język zmienia się od razu i jest zapamiętywany.
- Podaj wymiary samochodu w centymetrach: X — długość, Y — szerokość, Z — wysokość.
- Dodaj typy paczek: liczbę sztuk, wymiary, dozwolone obroty X/Y/Z i możliwość piętrowania.
- Opcja **Piętrowalna** oznacza, że na paczce można postawić inny towar.
- Kliknij **Oblicz ułożenie paczek**. Wynik i widoki pokazują znaleziony układ.
- Przykład: [8 paczek 123 × 83 × 50 cm](examples/eight-packages.json) mieści się
  w samochodzie 485 × 220 × 245 cm bez piętrowania, z różnymi orientacjami w dwóch rzędach.
- Konfiguracje JSON oraz historia i ulubione zachowują te same dane po zmianie języka.

### Ręczne układanie

- Klik w rzucie z góry — zaznacz paczkę; **Ctrl+klik** — zaznacz kilka.
- Przeciąganie jest płynne, bez skoków siatki 5 cm.
- Sąsiednie ściany paczek przyciągają się z odstępem **1 cm**; ściany samochodu bez odstępu.
- **Alt** — ruch bez przyciągania; **Esc** — anuluj przesuwanie.
- **R** — obróć zaznaczone paczki wokół Z, jeśli ten obrót jest dozwolony.
- **Delete** na liście „Typy paczek” — usuń zaznaczony typ i jego paczki z widoku.
- **Ctrl+Z** — cofnij przesuwanie, obrót, usunięcie lub edycję typu paczki.
- Kolizja, brak podparcia lub wyjście poza samochód powodują cofnięcie nieprawidłowego ruchu.
- Przesuwanie grup zachowuje wzajemne położenie paczek i nie zmienia kamery.

## English guide

Select **English** in the top-right corner; the preference is saved automatically.
Enter vehicle dimensions in centimetres and add package types with quantities, dimensions,
allowed rotations and stacking rules. **Stackable** means other cargo may be placed on top.
Click **Calculate packing** to search for a layout.

Click a package in the top view to select it; **Ctrl+click** selects several packages.
Drag to move with a **1 cm snap gap** between adjacent cargo faces. Vehicle walls have no padding.
Hold **Alt** to disable snapping, press **Esc** to cancel a move, or **R** to rotate around Z.
**Delete** in the package-type list removes the selected type; **Ctrl+Z** restores changes.
Invalid drops are reverted. Group movement preserves relative positions.

## Wyszukiwanie / Search limits

Algorytm próbuje różnych kolejności, obrotów, układów rzędów oraz pozycji wyznaczanych przez
ściany paczek; może cofać wcześniejsze wybory. Dodatkowe wyszukiwanie po szybkim układzie
początkowym ma limit 3 sekund i liczby odwiedzonych stanów. „Nie znaleziono pełnego układu”
oznacza wynik ograniczonego wyszukiwania, a nie matematyczny dowód braku miejsca.

Automatic packing tries multiple item orders, permitted orientations, row layouts and face-aligned
positions, with bounded backtracking. An incomplete result is not a mathematical proof that cargo cannot fit.
Automatic packing retains zero clearance between packages; the 1 cm gap applies to manual snapping.
Elevated packages require at least 50% footprint support, and cannot rest on non-stackable cargo.

## Uruchomienie źródeł / Run from source

Windows, Python 3.10+:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Można też uruchomić `run_app.bat`. Optional arguments: `--language pl`, `--language en`, `--version`.
Builds use Python 3.14 on Windows x64.

## Testy / Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover packing, allowed rotations, stacking, the eight-package regression, fixed obstacles,
manual snapping, dragging, collision rollback, Delete/Undo, language switching and preference persistence.
Qt integration tests create disposable windows and isolate application history/settings.

## Budowanie / Build

Install [Inno Setup 6.3+ or 7](https://jrsoftware.org/isdl.php) to compile the installer:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build.ps1 -Python .venv\Scripts\python.exe
```

The build script runs tests, builds the application with PyInstaller, compiles
[`installer/3DUltimator.iss`](installer/3DUltimator.iss), and writes the installer, portable ZIP
and `SHA256SUMS.txt` to `artifacts/`. Use `-ISCCPath` for a custom compiler location,
or `-SkipInstaller` to build only the portable release. `-SkipTests` is available for an already verified build.

GitHub Actions builds on pushes to `main`, pull requests and manual requests. Successful builds are
available as Actions artifacts. On `main`, a new version from `version.py` is published to Releases;
an existing release is preserved. Increase `version.py` before publishing the next version.
The same version is passed to the installer by `build.ps1`.

Application settings, personal package history and favorites are stored per user, outside the installation folder.
They are not included in the repository or release packages and are preserved by normal upgrades/uninstallation.
