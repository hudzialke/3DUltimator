# 3D Ultimator

**Project author: hudzialke. The program was implemented entirely by AI agents.**

Offline cargo-space planner for Windows with automatic 3D packing, manual placement,
and an interface available in English and Polish.

[English](#english) · [Polski](#polski)

## English

### Download

Download the application from [Releases](https://github.com/hudzialke/3DUltimator/releases/latest):

- **Setup EXE** — Windows x64 installer with English and Polish language options.
- **Portable ZIP** — extract the entire archive and run `3DUltimator.exe`.
- Python is not required to run either packaged version.
- Keep the `_internal` directory beside the executable.
- The installer installs for the current user without administrator privileges.

### Usage

Select **English** or **Polski** in the top-right corner. The interface changes immediately
and remembers your preference. Authorship and AI implementation are also disclosed under **Help → About**.

Enter the vehicle dimensions in centimetres: X — length, Y — width, Z — height.
Add package types with quantities, dimensions, allowed X/Y/Z rotations and stacking rules.
**Stackable** means other cargo may be placed on top of that package.
Click **Calculate packing** to search for a layout.

The [eight-package example](examples/eight-packages.json) fits eight 123 × 83 × 50 cm packages
in a 485 × 220 × 245 cm vehicle without stacking, using different orientations in two rows.
Changing language preserves cargo data, saved JSON field names, package history and favorites.

### Manual placement

- Click a package in the top view to select it; **Ctrl+click** selects multiple packages.
- Drag to move smoothly, without a coarse 5 cm grid.
- Adjacent cargo faces snap with a **1 cm gap**. Vehicle walls have no padding.
- Hold **Alt** to disable snapping; press **Esc** to cancel a move.
- **R** rotates selected packages around Z when that rotation is allowed.
- **Delete** in the package-type list removes the selected type and its displayed packages.
- **Ctrl+Z** restores a move, rotation, deletion or package-type edit.
- Invalid drops are reverted if they cause a collision, missing support or an out-of-bounds package.
- Group movement preserves relative positions and does not reset the camera.

### Search limits

Automatic packing tries multiple item orders, permitted rotations, row layouts and face-aligned
positions, with bounded backtracking. Additional search after the initial fast layout is limited
to 3 seconds and a maximum number of states. An incomplete result is not a mathematical proof
that cargo cannot fit. Automatic packing uses zero clearance between packages; the 1 cm gap
applies to manual snapping. Elevated packages require at least 50% footprint support and
cannot rest on non-stackable cargo.

### Run from source

Windows, Python 3.10+:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

You can also run `run_app.bat`. Optional arguments: `--language en`, `--language pl`, `--version`.
Packaged releases are built with Python 3.14 for Windows x64.

### Tests and builds

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover packing, allowed rotations, stacking, fixed obstacles, the eight-package regression,
manual snapping, dragging, Delete/Undo, language switching, saved preferences and authorship disclosure.
Qt integration tests use disposable windows and isolated history/settings.

Install [Inno Setup 6.3+ or 7](https://jrsoftware.org/isdl.php), then build:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build.ps1 -Python .venv\Scripts\python.exe
```

The build script runs tests, builds the app with PyInstaller, compiles
[`installer/3DUltimator.iss`](installer/3DUltimator.iss), and writes the installer, portable ZIP
and `SHA256SUMS.txt` to `artifacts/`. Use `-ISCCPath` for a custom compiler location,
`-SkipInstaller` for a portable-only build, or `-SkipTests` for an already verified build.

GitHub Actions builds on pushes to `main`, pull requests and manual requests. Successful builds
are available as Actions artifacts. On `main`, a new version from `version.py` is published to
Releases; an existing release is preserved. Increase `version.py` for the next release.
The build script passes that version to the installer.

Application settings, package history and favorites are stored per user outside the installation
folder. They are excluded from the repository and release packages, and preserved by normal upgrades and uninstallation.

---

## Polski

**Autor projektu: hudzialke. Program został w całości wykonany przez agentów AI.**

Program do planowania załadunku samochodu, działający offline na Windowsie,
z automatycznym układaniem 3D, ręcznym przesuwaniem oraz interfejsem polskim i angielskim.

### Pobieranie

Gotowy program znajduje się w [Releases](https://github.com/hudzialke/3DUltimator/releases/latest):

- **Setup EXE** — instalator Windows x64 z wyborem języka polskiego i angielskiego.
- **Portable ZIP** — rozpakuj cały plik ZIP i uruchom `3DUltimator.exe`.
- Python nie jest potrzebny do uruchamiania gotowego programu.
- Folder `_internal` musi pozostać obok `3DUltimator.exe`.
- Instalator działa dla bieżącego użytkownika, bez uprawnień administratora.

### Obsługa

Wybierz **Polski / English** w prawym górnym rogu. Język zmienia się od razu i jest zapamiętywany.
Informacja o autorze i wykonaniu przez agentów AI jest także w **Pomoc → O programie**.

Podaj wymiary samochodu w centymetrach: X — długość, Y — szerokość, Z — wysokość.
Dodaj typy paczek: liczbę sztuk, wymiary, dozwolone obroty X/Y/Z i możliwość piętrowania.
Opcja **Piętrowalna** oznacza, że na paczce można postawić inny towar.
Kliknij **Oblicz ułożenie paczek**, aby wyszukać układ.

[Przykład ośmiu paczek](examples/eight-packages.json) mieści osiem paczek 123 × 83 × 50 cm
w samochodzie 485 × 220 × 245 cm bez piętrowania, z różnymi orientacjami w dwóch rzędach.
Zmiana języka zachowuje dane ładunku, pola zapisanych konfiguracji JSON, historię i ulubione.

### Ręczne układanie

- Klik w rzucie z góry zaznacza paczkę; **Ctrl+klik** zaznacza kilka.
- Przeciąganie jest płynne, bez skoków siatki 5 cm.
- Sąsiednie ściany paczek przyciągają się z odstępem **1 cm**; ściany samochodu bez odstępu.
- **Alt** wyłącza przyciąganie; **Esc** anuluje ruch.
- **R** obraca zaznaczone paczki wokół Z, jeśli obrót jest dozwolony.
- **Delete** na liście typów usuwa zaznaczony typ i jego paczki z podglądu.
- **Ctrl+Z** cofa przesuwanie, obrót, usunięcie lub edycję typu paczki.
- Kolizja, brak podparcia lub wyjście poza samochód powodują cofnięcie nieprawidłowego ruchu.
- Przesuwanie grup zachowuje wzajemne położenie paczek i nie zmienia kamery.

### Ograniczenia wyszukiwania

Algorytm próbuje różnych kolejności, obrotów, układów rzędów i pozycji wyznaczanych przez
ściany paczek oraz cofa wcześniejsze wybory. Dodatkowe wyszukiwanie po szybkim układzie
początkowym ma limit 3 sekund i liczby stanów. Brak pełnego układu nie jest matematycznym
dowodem braku miejsca. Automatyczne układanie zachowuje brak odstępów między paczkami;
odstęp 1 cm dotyczy ręcznego przyciągania. Paczka ponad podłogą wymaga podparcia co najmniej
50% powierzchni podstawy i nie może opierać się na paczce niepiętrowalnej.

### Uruchomienie źródeł

Wymagany Windows i Python 3.10+. Utwórz środowisko, zainstaluj zależności i uruchom program:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Można też uruchomić `run_app.bat`. Dostępne argumenty: `--language pl`, `--language en`, `--version`.
Gotowe wydania są budowane w Pythonie 3.14 dla Windows x64.

### Testy i budowanie

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Testy obejmują układanie, obroty, piętrowanie, stałe przeszkody, przypadek ośmiu paczek,
przyciąganie, przeciąganie, Delete/Ctrl+Z, języki, zapamiętywanie wyboru i informację o autorstwie.
Testy Qt używają tymczasowych okien oraz odizolowanych ustawień i historii.

Zainstaluj [Inno Setup 6.3+ lub 7](https://jrsoftware.org/isdl.php), a następnie:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build.ps1 -Python .venv\Scripts\python.exe
```

Skrypt uruchamia testy, buduje aplikację i kompiluje `installer/3DUltimator.iss`.
Instalator, ZIP i sumy SHA-256 trafiają do `artifacts/`. Parametr `-ISCCPath` wskazuje kompilator,
`-SkipInstaller` pomija instalator, a `-SkipTests` pomija wcześniej wykonane testy.

GitHub Actions buduje projekt po zmianach na `main`, dla pull requestów i na żądanie.
Nowa wersja z `version.py` trafia do Releases; istniejące wydania pozostają bez zmian.
Przed następnym wydaniem zwiększ numer w `version.py`. Skrypt przekazuje go instalatorowi.

Ustawienia, osobista historia i ulubione są zapisywane osobno dla każdego użytkownika,
poza katalogiem instalacji. Nie trafiają do repozytorium ani paczek wydania i pozostają po standardowej aktualizacji lub odinstalowaniu.
