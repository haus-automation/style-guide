# psd-tool – Schriftarten in PSD-Dateien auflisten

`psd_fonts.py` liest PSD- und PSB-Dateien und listet alle Schriften auf, die in Textebenen
tatsächlich verwendet werden, getrennt nach Datei. Ebenen in Gruppen, ausgeblendete Ebenen
und Textebenen in eingebetteten Smartobjekten sind dabei mit eingeschlossen. Schriften, die zwar in der Datei hinterlegt sind, aber von keinem Text
verwendet werden, ignoriert das Script.

Die Dateien werden nur gelesen, nie verändert. Zusätzlich bindet der Docker-Aufruf unten
das Verzeichnis schreibgeschützt (`:ro`) ein, sodass der Container gar nicht schreiben kann.

## Voraussetzungen

- Docker (z. B. Docker Desktop für macOS)

## Image bauen

Einmalig in diesem Verzeichnis (`psd-tool/`) ausführen:

```sh
docker build -t psd-fonts .
```

Wenn du `psd_fonts.py` änderst, musst du das Image neu bauen.

## Verwendung

Wechsle in das Verzeichnis mit deinen PSD-Dateien und starte den Container. Das aktuelle
Verzeichnis wird schreibgeschützt nach `/data` im Container eingebunden. Pfade gibst du
relativ zu diesem Verzeichnis an.

### Schriften je Datei

```sh
cd ~/Pfad/zu/den/PSDs
docker run --rm -v "$PWD":/data:ro psd-fonts .
```

Unterordner werden rekursiv durchsucht. Du kannst auch einzelne Dateien oder mehrere
Ordner angeben:

```sh
docker run --rm -v "$PWD":/data:ro psd-fonts header.psd kampagne/ social/
```

Beispielausgabe:

```
== kampagne/header.psd
   Montserrat-Bold                          24, 48 pt
   Montserrat-Regular                       14 pt         [auch in ausgeblendeten Ebenen]
   Helvetica                                18 pt         [nur in ausgeblendeten Ebenen]
   ! verknuepftes Smartobjekt nicht gelesen: [Logo] -> logo.psb

== social/post.psd
   ArialMT                                  12 pt
```

Für jede Datei siehst du die verwendeten Schriften und die vorkommenden Schriftgrößen.
Angezeigt werden die PostScript-Namen der Schriften, also z. B. `Montserrat-Bold` statt
„Montserrat Bold“.

Schriften aus ausgeblendeten Ebenen werden gekennzeichnet:

- `[nur in ausgeblendeten Ebenen]`: Die Schrift kommt nur in unsichtbarem Text vor.
- `[auch in ausgeblendeten Ebenen]`: Die Schrift wird sichtbar verwendet, steckt aber
  zusätzlich in ausgeblendeten Ebenen.

Als ausgeblendet gilt eine Textebene auch, wenn ihre Gruppe oder das Smartobjekt, in dem
sie liegt, ausgeblendet ist. Zeilen mit `!` sind Hinweise, z. B. auf verknüpfte Smartobjekte. Deren
Inhalt liegt in einer externen Datei und kann daher nicht mit ausgewertet werden.

### Details je Textebene (`-v`)

```sh
docker run --rm -v "$PWD":/data:ro psd-fonts -v .
```

Zusätzlich wird je Datei jede Textebene mit Schrift, Größe (pt) und den ersten 60 Zeichen
des Texts aufgelistet. Ausgeblendete Ebenen sind mit `(ausgeblendet)` markiert, Ebenen in
Smartobjekten erscheinen als `[Smartobjekt > Ebene]`.

### Gesamtübersicht (`--summary`)

```sh
docker run --rm -v "$PWD":/data:ro psd-fonts --summary .
```

Hängt am Ende eine Übersicht an, welche Schrift in wie vielen Dateien vorkommt.

### CSV-Export (`--csv`)

```sh
docker run --rm -v "$PWD":/data:ro psd-fonts --csv . > fonts.csv
```

Die CSV-Datei verwendet `;` als Trennzeichen (passt für Excel und Numbers mit deutschen
Einstellungen) und hat die Spalten `datei;ebene;text;font;groesse_pt;sichtbar`. Die Spalte `sichtbar` enthält
`ja` oder `nein`. Die Umleitung
`> fonts.csv` schreibt die Datei auf deinem Mac, nicht im Container. Die PSD-Ordner bleiben
also weiterhin schreibgeschützt eingebunden.

### Hilfe anzeigen

```sh
docker run --rm psd-fonts --help
```

## Hinweise

- Dateien, die nicht gelesen werden können, werden mit `!! <datei>: <fehler>` auf stderr
  gemeldet und übersprungen. Der Rest wird trotzdem ausgewertet.
- Liegen die PSDs außerhalb des aktuellen Verzeichnisses, binde stattdessen diesen Ordner
  ein, z. B. `-v ~/Projekte/Design:/data:ro`, und gib Pfade relativ dazu an.
- Pfade mit Leerzeichen in Anführungszeichen setzen: `"Kunde A/Entwurf 1.psd"`.
- Ohne Docker geht es auch direkt mit Python 3: `pip install psd-tools`, dann
  `python3 psd_fonts.py <pfade>`.
