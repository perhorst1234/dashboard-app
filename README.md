# Dashboard Project

## Algemene Idee
- Fysiek dashboard met schuifregelaars en knoppen voor volumebediening, app-opstart, scripts, toetscombinaties en systeembewaking.
- Kan werken in hardware-modus (Arduino/ESP32) of testmodus (PC-simulatie).

## Fysieke Afmetingen
- **Afmetingen behuizing:** 656,641 mm (l) × 180 mm (b)
- **Knoppen:**
  - Twee verticale kolommen van vier knoppen aan weerszijden van de sliders (links btn0–btn7, rechts btn8–btn15)
  - Bovenste rij begint 46 mm van de bovenzijde; iedere volgende rij ligt 24,67 mm lager (14,07 mm knop + 10,6 mm ruimte)
  - Kolommen staan 25 mm uit de zijkant met 24,67 mm horizontale afstand tussen kolom 1 en 2
  - Afmetingen: 14,07 mm × 14,07 mm
- **Sliders:**
  - 4 schuifregelaars, 65 mm lang en 2 mm breed
  - Posities (linkerbovenhoek):
    - Slider 1: 165,344 mm links, 56,981 mm boven
    - Slider 2: 205,852 mm links, 56,981 mm boven
    - Slider 3: 447,852 mm links, 56,981 mm boven
    - Slider 4: 489,296 mm links, 56,981 mm boven

## Hardware Connectie
- Arduino/ESP32 verstuurt data via een seriële lijn op 9600 baud.
- Datapakket: `slider1|slider2|slider3|slider4|btn0|btn1|...|btn15`
- Sliders rapporteren waarden van 0–1023 (0 onder, 1023 boven).
- Knoppen gebruiken rising edge-detectie voor activatie.

## Slider Functionaliteit
- Toewijzing aan volumes van geïnstalleerde of actieve apps.
- Mapping 0–1023 naar 0–100% via de ingebouwde Windows CoreAudio API.
- UI-sliderknoppen bewegen mee met hardware-input.

## Knoppen Functionaliteit
- Mogelijke acties:
  - Apps openen (met icoonselectie uit geïnstalleerde lijst)
  - Scripts uitvoeren (bestand + optionele argumenten)
  - Toetscombinaties versturen (vooraf gedefinieerd of custom, bijv. Ctrl+Shift+S)
- Knoppen lichten op bij rising edge-input van de hardware.

## Software Functionaliteit
- UI volgt de fysieke layout en schaalt met het scherm.
- Hover-effect: gloed voor sliders en knoppen.
- Instant search met lokale index en caching (Start Menu + Program Files).
- Instellingen worden opgeslagen in JSON, automatisch geladen en kunnen worden gereset naar defaults.
- Configuratiescherm in de app om sliders, knoppen, seriële instellingen én fysieke posities aan te passen.
- Slider-tab bevat een knop **Actieve apps** die actuele Windows-audiosessies toont zodat je direct het juiste proces kunt kiezen voor volumekoppelingen.
- Nieuwe layout-tab met live preview zodat de digitale weergave exact overeenkomt met de behuizing.

## Extra Features
- Toggle tussen hardware- en testmodus voor simulatie zonder fysieke hardware.
- Realtime updates van sliders en knoppen via seriële data.
- Volume- en appcontrole via native Windows CoreAudio-aanroepen (geen externe tools meer nodig) inclusief een live lijst van actieve audio-apps om snel targets te koppelen.
- Automatische schermschaal voor optimale weergave.
- In-app configuratiescherm voor sliders, knoppen, seriële instellingen (COM-poort en baudrate) en layout.
- Toetscombinaties kunnen direct in de UI worden opgenomen door de gewenste toetsen in te drukken, inclusief functie- en speciale toetsen.

---

## Software-installatie

```bash
pip install .
```

Hiermee worden de Qt-gebaseerde interface en optionele afhankelijkheden zoals `pyserial` en `pyautogui` geïnstalleerd.

## Applicatie starten

```bash
python -m dashboard_app --mode test
```

Of gebruik de console-script:

```bash
dashboard-app --mode test
```

Belangrijke opties:

- `--mode {test,hardware}`: start direct in test- of hardwaremodus.
- `--serial-port`: overschrijft de standaard seriële poort (bijv. `COM3`, `/dev/ttyUSB0`).
- `--baudrate`: overschrijft de standaard baudrate van 9600.
- `--config`: pad naar een alternatieve JSON-configuratie.

## Testmodus

- De sliders in de UI kunnen vrij bewogen worden; elke wijziging wordt geprojecteerd als een hardwarepakket zodat de logica gelijk blijft.
- Knoppen sturen direct de geconfigureerde acties (app openen, script starten of toetscombinatie versturen).
- Instellingen worden opgeslagen in `dashboard-settings.json` (in `%APPDATA%` op Windows of de home-map op andere systemen).

## Hardwaremodus

- Activeer hardwaremodus via de werkbalk of startopties.
- De app probeert `pyserial` te gebruiken om seriële data te lezen en de UI synchroon te houden met het fysieke dashboard.
- Gebruik het configuratiescherm (werkbalk → "Configure Dashboard") om COM-poort en baudrate te selecteren of hardwaremodus in/uit te schakelen.
- Elk ontvangen hardwarepakket update sliders (0–1023 → 0–100%) en vuurt bij rising edges de bijbehorende knopactie.

## Volume-aansturing

- Op Windows gebruikt de app de CoreAudio API om systeem- en appvolumes rechtstreeks te wijzigen.
- Bij app-specifieke sliders wordt gezocht naar een actieve audiosessie waarvan de procesnaam overeenkomt met de opgegeven hint (bijv. `chrome` of `chrome.exe`).
- Op andere platformen wordt de volumewijziging gelogd maar niet uitgevoerd.

## Afhankelijkheden

- [PySide6](https://doc.qt.io/qtforpython/) voor de UI.
- [pyserial](https://pyserial.readthedocs.io/) voor seriële communicatie.
- [pyautogui](https://pyautogui.readthedocs.io/) voor toetsenbordautomatisering (optioneel).

## Ontwikkeling

- `pyproject.toml` definieert de projectmetadata en dependencies.
- De belangrijkste modules bevinden zich in `dashboard_app/`:
  - `config.py`: laad- en opslaglogica voor instellingen.
  - `controller.py`: koppelt hardware, UI en acties.
  - `hardware.py`: seriële leesthread en payloadparser.
  - `actions/`: implementatie van volume-, script- en toetsacties.
  - `ui/main_window.py`: Qt-interface met sliders, knoppen en modusknoppen.
  - `ui/config_dialog.py`: dialoog om slider-/knopacties en seriële verbinding te configureren.

## Bekende beperkingen

- Volume-aanpassing werkt alleen op Windows (CoreAudio). Op andere platforms wordt de wijziging alleen gelogd.
- Voor toetscombinaties is Windows SendInput beschikbaar; anders wordt teruggevallen op `pyautogui` wanneer geïnstalleerd.
- PySide6 vereist een werkende Qt-runtime; installeer systeemafhankelijkheden indien nodig.
