"""Polish/English messages and live translation of Qt widget properties.

Polish source messages remain stable keys. Saved cargo and package history use
language-independent field names; only their presentation is translated.
"""

LANGUAGES = ("pl", "en")
_language = "pl"
_qt_translator = None

EN = {
    "Język:": "Language:",
    "Tak": "Yes", "Nie": "No", "brak": "none",
    "Ilość": "Quantity", "Piętrowalna": "Stackable",
    "Rot X": "Rotate X", "Rot Y": "Rotate Y", "Rot Z": "Rotate Z",
    "Plik": "File", "Cofnij": "Undo", "Obróć Z": "Rotate Z",
    "Anuluj przesuwanie": "Cancel move", "Usuń typ paczki": "Delete package type",
    "Zapisz konfigurację…": "Save configuration…",
    "Wczytaj konfigurację…": "Load configuration…",
    "Zapisz konfigurację": "Save configuration",
    "Wczytaj konfigurację": "Load configuration",
    "Konfiguracja ładunku (*.json);;Wszystkie pliki (*.*)": "Cargo configuration (*.json);;All files (*.*)",
    "Wymiary przestrzeni ładunkowej [cm]:": "Cargo space dimensions [cm]:",
    "X (długość)": "X (length)", "Y (szerokość)": "Y (width)", "Z (wysokość)": "Z (height)",
    "X (długość):": "X (length):", "Y (szerokość):": "Y (width):", "Z (wysokość):": "Z (height):",
    "Typy paczek (lista — edycja w osobnym oknie):": "Package types (double-click a row to edit):",
    "Dodaj typ paczki…": "Add package type…", "Edytuj…": "Edit…", "Usuń": "Delete",
    "Historia…": "History…", "★ Ulubione…": "★ Favorites…",
    "Paczki używane wcześniej — przywróć do puli": "Previously used packages — add to the list",
    "Zapisane ulubione typy paczek": "Saved favorite package types",
    "Pokazuj paczki, które się nie zmieściły": "Show packages that did not fit",
    "Oblicz ułożenie paczek": "Calculate packing",
    "Przelicza cały układ od zera (auto).": "Recalculate the entire layout automatically.",
    "Wstaw nowe bez układu": "Add new packages for manual placement",
    "Dodaje brakujące sztuki z listy typów obok busy (overflow),\nbez ruszania już ułożonych paczek. Potem przeciągnij je myszą.":
        "Add missing packages beside the vehicle without moving existing cargo.\nThen drag them into place.",
    "Obróć zaznaczone o 90° (Z)": "Rotate selected by 90° (Z)",
    "Obraca tylko zaznaczone paczki (X↔Y) w miejscu — inne nie zmieniają położenia.":
        "Rotate selected packages around Z (X↔Y); other packages stay in place.",
    "Zaznaczanie: klik w rzut z góry (Ctrl+klik = wiele). Przeciąganie: przyciąganie z odstępem 1 cm; Alt = bez przyciągania. Esc = anuluj ruch. R = obrót Z. Delete na liście = usuń typ. „Wstaw nowe bez układu” dorzuca paczki obok busy do ręcznego ustawienia.":
        "Click in the top view to select (Ctrl+click for multiple). Drag to move; snap gap: 1 cm. Alt: disable snapping. Esc: cancel move. R: rotate Z. Delete in the list: delete type. Add new packages for manual placement puts them beside the vehicle.",
    "Werdykt: brak obliczenia": "Result: not calculated",
    "Werdykt: brak paczek": "Result: no packages",
    "Werdykt: POPRAW UŁOŻENIE — kolizja lub brak podparcia": "Result: FIX LAYOUT — collision or missing support",
    "Werdykt: MIEŚCI SIĘ — wszystkie {fitted} paczek": "Result: FITS — all {fitted} packages",
    "Werdykt: NIE ZNALEZIONO PEŁNEGO UKŁADU — poza: {overflow} / {total}":
        "Result: NO COMPLETE LAYOUT FOUND — outside: {overflow} / {total}",
    "W środku: {fitted}  |  Overflow: {overflow}\nObjętość użyta: {used:.0f} / {vol_box:.0f} cm3  ({fill_pct:.1f}%)":
        "Inside: {fitted}  |  Outside: {overflow}\nVolume used: {used:.0f} / {vol_box:.0f} cm3  ({fill_pct:.1f}%)",
    "Rzut z góry (X/Y) — klik: zaznacz": "Top view (X/Y) — click to select",
    "Rzut z boku (X/Z)": "Side view (X/Z)",
    "Dodaj typ paczki": "Add package type", "Edytuj typ paczki": "Edit package type",
    " szt.": " pcs", "Ilość sztuk:": "Quantity:",
    "Wymiary paczki [cm]": "Package dimensions [cm]", "Opcje układania": "Packing options",
    "Piętrowalna (można stawiać coś na wierzchu)": "Stackable (other cargo may be placed on top)",
    "Dozwolone obroty o 90°:": "Allowed 90° rotations:",
    "Wokół osi X (zamiana Y ↔ Z)": "Around X (swap Y ↔ Z)",
    "Wokół osi Y (zamiana X ↔ Z)": "Around Y (swap X ↔ Z)",
    "Wokół osi Z (zamiana X ↔ Y)": "Around Z (swap X ↔ Y)",
    "★ Ulubiona (zapisz na liście ulubionych)": "★ Favorite (save to favorites)",
    "Zapisz": "Save", "Anuluj": "Cancel", "Zamknij": "Close",
    "Ulubione paczki ★": "Favorite packages ★", "Historia paczek": "Package history",
    "Brak ulubionych. Oznacz paczkę gwiazdką przy dodawaniu/edycji.":
        "No favorites yet. Mark a package with a star when adding or editing it.",
    "Historia jest pusta. Dodane typy paczek pojawią się tutaj.":
        "History is empty. Package types you add will appear here.",
    "Zaznacz wpis i kliknij „Dodaj do puli”, albo dwukrotnie kliknij wiersz.\nHistoria i ulubione są zapamiętane po zamknięciu programu.":
        "Select an entry and click Add to list, or double-click a row.\nHistory and favorites are saved when the application closes.",
    "★ Ulubiona": "★ Favorite", "★ Dodaj do ulubionych": "★ Add to favorites",
    "Usuń z listy": "Remove from list", "Dodaj do puli": "Add to list",
    "\n    ostatnio: {last_used}": "\n    last used: {last_used}",
    "piętrowalna": "stackable", "niepiętrowalna": "not stackable",
    "{count} szt.  |  {dx}×{dy}×{dz} cm  |  {stack}  |  rot: {rot_txt}":
        "{count} pcs  |  {dx}×{dy}×{dz} cm  |  {stack}  |  rotations: {rot_txt}",
    "Wybór": "Selection", "Zaznacz paczkę na liście.": "Select a package in the list.",
    "Edycja": "Edit", "Zaznacz typ paczki na liście, potem kliknij Edytuj.":
        "Select a package type in the list, then click Edit.",
    "Wstawianie": "Add packages",
    "Brak nowych sztuk do wstawienia.\nZwiększ „Ilość” w typie paczki albo dodaj nowy typ.":
        "No new packages to add.\nIncrease the quantity of a package type or add a new type.",
    "Dodano {added} paczek obok przestrzeni ładunkowej.\nPrzeciągnij je myszą w rzucie z góry we właściwe miejsce.":
        "Added {added} packages beside the cargo space.\nDrag them into place in the top view.",
    "Uwaga: ": "Warning: ", "Paczka {number}: {detail}.": "Package {number}: {detail}.",
    "wychodzi poza lewą krawędź": "extends beyond the left edge",
    "wychodzi poza dolną krawędź": "extends beyond the lower edge",
    "schodzi poniżej podłogi": "extends below the floor",
    "wychodzi poza długość X": "exceeds cargo length X",
    "wychodzi poza szerokość Y": "exceeds cargo width Y",
    "wychodzi poza wysokość Z": "exceeds cargo height Z",
    "poza przestrzenią ładunkową": "outside the cargo space",
    "koliduje z paczką {number}": "collides with package {number}",
    "brak podparcia lub obciążenie paczki niepiętrowalnej": "missing support or load on a non-stackable package",
    "Ruch cofnięty: kolizja, brak podparcia lub paczka poza samochodem.":
        "Move reverted: collision, missing support, or package outside the vehicle.",
    "Obrót Z": "Rotate Z",
    "Zaznacz paczki w rzucie z góry (klik / Ctrl+klik), potem naciśnij R.":
        "Select packages in the top view (click / Ctrl+click), then press R.",
    "Brak zaznaczonych paczek.": "No packages selected.",
    "Obrót Z jest wyłączony dla zaznaczonej paczki.": "Z rotation is disabled for a selected package.",
    "Obrót cofnięty: kolizja, brak podparcia lub brak miejsca.":
        "Rotation reverted: collision, missing support, or insufficient space.",
    "Błąd zapisu": "Save error", "Błąd odczytu": "Load error",
    "Nie udało się zapisać pliku:\n{error}": "Could not save the file:\n{error}",
    "Nie udało się wczytać pliku:\n{error}": "Could not load the file:\n{error}",
}


def language():
    return _language


def set_language(code):
    global _language
    if code not in LANGUAGES:
        code = "pl"
    _language = code


def configure_qt_language():
    """Translate standard Qt buttons and dialogs as well as app messages."""
    from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

    global _qt_translator
    app = QCoreApplication.instance()
    if app is None:
        return
    if _qt_translator is not None:
        app.removeTranslator(_qt_translator)
        _qt_translator = None
    QLocale.setDefault(QLocale("pl_PL" if _language == "pl" else "en_US"))
    if _language == "pl":
        translator = QTranslator(app)
        if translator.load("qtbase_pl", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator)
            _qt_translator = translator


def tr(source, **values):
    message = EN.get(source, source) if _language == "en" else source
    return message.format(**values) if values else message


def apply_translations(root):
    """Bind original text to each Qt object, then translate without rebuilding.

    Only catalogued strings are bound. Numbers, cargo labels, user input and
    dynamically formatted result messages are left to their explicit renderers.
    """
    from PySide6.QtCore import QObject

    reverse = {value: key for key, value in EN.items()}
    for obj in [root, *root.findChildren(QObject)]:
        for getter, setter in (("text", "setText"), ("title", "setTitle"),
                               ("windowTitle", "setWindowTitle"), ("toolTip", "setToolTip"),
                               ("suffix", "setSuffix")):
            read, write = getattr(obj, getter, None), getattr(obj, setter, None)
            if not callable(read) or not callable(write):
                continue
            property_name = "_i18n_" + getter
            source = obj.property(property_name)
            if source is None:
                current = read()
                if not isinstance(current, str):
                    continue
                source = current if current in EN else reverse.get(current)
                if source is None:
                    continue
                obj.setProperty(property_name, source)
            write(tr(source))
