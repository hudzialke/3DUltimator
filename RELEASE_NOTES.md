# 3D Ultimator 1.1.2

**Project author: hudzialke. The program was implemented entirely by AI agents.**

- Fix a QtCore DLL startup failure caused by unrelated DLLs collected from the developer environment.
- Restrict DLL discovery to Python and Windows; reject dependencies from unrelated tools.
- Verify the actual packaged EXE, Qt startup, eight-package packing and language switching before publishing.
- Replace the private runtime directory during installer upgrades to remove stale DLLs.
- English documentation first, followed by Polish; authorship and AI implementation in Help → About and AUTHORS.md.
- Polish/English interface, improved packing, smooth dragging with a 1 cm snap gap, Delete and Ctrl+Z.

Download the **Setup EXE** to install, or extract the **portable ZIP** and run `3DUltimator.exe`.
Extract a portable release into an empty folder. Keep `_internal` beside the executable.
Checksums are in `SHA256SUMS.txt`.

---

**Autor projektu: hudzialke. Program został w całości wykonany przez agentów AI.**

- Naprawa błędu startu QtCore spowodowanego niepasującymi DLL ze środowiska budowania.
- Wyszukiwanie DLL ograniczone do Pythona i Windowsa, z blokadą zależności z innych narzędzi.
- Test gotowego EXE: start Qt, przykład ośmiu paczek i zmiana języka przed publikacją.
- Instalator zastępuje prywatny folder bibliotek, usuwając nieaktualne DLL przy aktualizacji.
- Dokumentacja najpierw po angielsku, potem po polsku; autorstwo i wykonanie przez AI w Pomoc → O programie i AUTHORS.md.
- Interfejs PL/EN, lepsze układanie, płynne przesuwanie z odstępem 1 cm, Delete i Ctrl+Z.

Pobierz **Setup EXE**, aby zainstalować program, albo rozpakuj **Portable ZIP** do pustego folderu.
Zachowaj `_internal` obok `3DUltimator.exe`. Sumy kontrolne są w `SHA256SUMS.txt`.
