# speech.cpp auf der Radeon 890M: Messungen vom 18.11.2026

Sammlung aller Messwerte aus einer Sitzung, als Faktenbasis für einen Artikel. Die TTS-Zahlen der
[Messreihe](#messreihe-3-runden-je-10-sätze) beruhen auf 30 Sätzen je Konfiguration in drei Runden. Alle
anderen Zahlen stammen aus Einzelläufen, so steht es jeweils dabei.

## Kernaussagen

- **Läuft auf der 890M:** speech.cpp bringt Qwen3-TTS und Qwen3-ASR auf die integrierte Radeon 890M, mit
  Vulkan wie mit ROCm, ohne Änderung am Code und ohne `HSA_OVERRIDE`. Vulkan ist dort rund 18 % schneller
  als ROCm.
- **TTS in Echtzeit:** Qwen3-TTS 0.6B spricht 2,2-mal, 1.7B 1,6-mal so schnell wie Echtzeit; das erste
  Audio kommt nach 50 bzw. 67 ms (Median, warm). Gemessen an der Zeit, bis ein Text gesprochen ist, ist
  1.7B nur 13 % langsamer als 0.6B.
- **TTS-Schwächen:** Gelegentlich Kauderwelsch, vor allem bei Sätzen mit Deutsch und Englisch (etwa jeder
  vierte); Vulkan liefert mit gleichem Seed nicht reproduzierbar dasselbe Audio.
- **STT schneller und zweisprachig:** Qwen3-ASR 1.7B erkennt echte Sprache über ein Echo Show 5 so genau
  wie faster-whisper (large-v3-turbo) und braucht dafür die Hälfte der Zeit (p50 0,48 s gegen 0,90 s).
  faster-whisper mit fester Sprache übersetzte 5 von 6 englischen Sätzen ins Deutsche; Qwen3-ASR erkannte
  alle im Original.

## Aufbau

| | |
|---|---|
| Rechner | Minisforum, AMD Ryzen AI 9 HX 370 (12 Kerne / 24 Threads), Radeon 890M (gfx1150, RDNA 3.5, 16 CUs), 62 GB RAM, von CPU und GPU geteilt |
| Host | Ubuntu 24.04, Linux 7.0, Docker; kein ROCm auf dem Host |
| speech.cpp | 0.11.0 (Commit 8d18924), ggml-Fork 0.27.0 (Commit 79b50d23) |
| ROCm-Build | im Container `rocm/dev-ubuntu-24.04:7.14.1-full` (HIP 7.14), `-DGGML_HIP=ON -DGPU_TARGETS=gfx1150` |
| Vulkan-Build | im Container `ubuntu:24.04` mit Mesa RADV, `-DGGML_VULKAN=ON`; für die Dienste das offizielle Release-Archiv `speech-0.11.0-linux-x64-vulkan.zip` |
| Modelle | jeweils Q8_0 aus dem Katalog von speech.cpp |
| Nebenlast | Auf derselben GPU liefen währenddessen weitere Dienste (u. a. llama.cpp-Server mit Vulkan, Whisper mit ROCm). Die Werte sind also Alltags-, keine Laborwerte. |

**Maß:** RTFx = Sekunden Audio pro Sekunde Rechenzeit; größer ist schneller, 1,0 ist Echtzeit. „Erstes
Audio“ = Zeit von der Anfrage bis zum ersten Audio-Chunk.

**ROCm-Befund:** Die 890M läuft mit ROCm 7.14 nativ als gfx1150, ohne `HSA_OVERRIDE_GFX_VERSION`. Am Code
von speech.cpp war nichts zu ändern; die Gerätewahl nimmt jede GPU, die ggml meldet. Offiziell unterstützt
speech.cpp unter Linux nur Vulkan und die CPU.

| Gerät, wie `speech devices` es meldet | Speicher |
|---|---|
| `ROCm0` AMD Radeon 890M Graphics | 33,0 GB |
| `Vulkan0` AMD Radeon 890M Graphics (RADV GFX1150) | 52,6 GB |
| `CPU` AMD Ryzen AI 9 HX 370 | 66,0 GB |

## Modelldateien

| Modell | Datei (Q8_0) | Download |
|---|---|---|
| qwen3-tts-0.6b (CustomVoice) | 1,21 GB | 42 s |
| qwen3-tts-1.7b (CustomVoice) | 2,29 GB | nicht gemessen |
| qwen3-asr-0.6b | 0,84 GB | 29 s |
| qwen3-asr-1.7b | 2,18 GB | 74 s |

Ladezeit: TTS 0.6B 0,64 s auf ROCm, 0,73 s auf der CPU. ASR 0.6B 0,75 s auf ROCm, 0,30 s auf der CPU.
ASR 1.7B 1,44 s auf Vulkan.

## TTS: Qwen3-TTS

### Messreihe: 3 Runden je 10 Sätze

**Aufbau:** 10 deutsche Assistenten-Sätze, von „Hallo, ich bin bereit.“ (2 Wörter) bis zu einem Satz mit
33 Wörtern. Stimme `ono_anna`, Sprache `de`, Seeds 1, 2 und 3. Jede Runde ist ein Prozess; ein
Aufwärmsatz vorweg wird nicht mitgezählt, damit die Werte denen eines laufenden Servers entsprechen. Je
Konfiguration ergibt das 30 Messungen. Das Ganze lief am 18.11.2026 von 12:25 bis 12:35 Uhr. Die anderen
Dienste auf der GPU liefen weiter; ob sie in der Zeit gearbeitet haben, ist nicht erfasst. Um 12:29 lief
eine kurze Spracherkennung (3,4 s Audio) parallel zur zweiten Runde von 1.7B auf Vulkan.

| Konfiguration | RTFx gesamt | RTFx je Runde | RTFx je Satz p50 / p10 | Erstes Audio p50 / p90 / max | Audio gesamt | Rechenzeit gesamt |
|---|---|---|---|---|---|---|
| 0.6B, Vulkan | **2,16** | 2,17 / 2,14 / 2,16 | 2,17 / 2,14 | **50 / 64 / 109 ms** | 184,0 s | 85 s |
| 0.6B, ROCm | 1,83 | 1,84 / 1,81 / 1,83 | 1,82 / 1,76 | 59 / 66 / 98 ms | 165,0 s | 90 s |
| 1.7B, Vulkan | **1,56** | 1,55 / 1,58 / 1,56 | 1,56 / 1,53 | **67 / 91 / 122 ms** | 149,5 s | 96 s |
| 1.7B, ROCm | 1,31 | 1,37 / 1,37 / 1,19 | 1,34 / 1,16 | 84 / 88 / 189 ms | 150,2 s | 115 s |
| 0.6B, CPU | 1,21 | 1,28 / 1,20 / 1,16 | 1,25 / 1,05 | 114 / 166 / 232 ms | 176,9 s | 146 s |

RTFx gesamt = Summe Audio durch Summe Rechenzeit. p10 bei RTFx ist der langsame Rand: 9 von 10 Sätzen
waren schneller. „Rechenzeit gesamt“ ist die Zeit für alle 30 Sätze.

Erstes Audio beim **ersten** Satz eines Prozesses (Aufwärmsatz, je Runde):

| | Vulkan | ROCm | CPU |
|---|---|---|---|
| 0.6B | 0,65 / 0,68 / 0,70 s | 0,24 / 0,23 / 0,21 s | 0,10 / 0,10 / 0,15 s |
| 1.7B | 0,64 / 0,70 / 0,68 s | 0,26 / 0,22 / 0,24 s | – |

Ergebnisse:

- **Vulkan ist auf der 890M das schnellste Backend**, gut 18 % vor ROCm (0.6B: 2,16 gegen 1,83; 1.7B:
  1,56 gegen 1,31). Die Einzelläufe am Anfang hatten das nicht gezeigt.
- **Die Werte sind stabil:** Die Runden einer Konfiguration liegen auf Vulkan innerhalb von ±2 %. Ausreißer
  ist eine ROCm-1.7B-Runde mit 1,19 statt 1,37.
- **Warm kommt das erste Audio nach 50–70 ms** (Median, Vulkan). Auch der langsamste von 30 Sätzen lag
  unter 125 ms.
- **Kalt ist Vulkan beim ersten Satz langsamer** (0,65–0,70 s gegen 0,21–0,26 s mit ROCm). Danach ist der
  Unterschied weg. `speech serve` wärmt das Modell beim Start auf, im Dienst spielt das also keine Rolle.
- **0.6B macht längeres Audio:** Für dieselben 30 Sätze 184 s gegen 150 s beim 1.7B. Die Projektdoku
  erwähnt, dass das 0.6B oft mit Stille beginnt. Das schönt den RTFx des 0.6B: Gemessen an der Zeit, bis
  alle 30 Sätze gesprochen sind, ist 1.7B nur 13 % langsamer (96 s gegen 85 s), nicht 28 %.
- **Die Länge eines Satzes streut stark mit dem Seed.** „Hallo, ich bin bereit.“ dauerte je nach Seed und
  Modell 1,2 bis 4,7 s, Satz 5 beim 1.7B auf Vulkan 3,5 bis 8,8 s. Das ist Sampling, kein Messfehler.
- Die CPU kommt in dieser Reihe auf 1,21 statt 1,4 im Einzellauf; die Runden streuen hier am meisten
  (1,16–1,28).

### Erste Einzelmessungen: Backends im Vergleich (0.6B, ein Text, frischer Prozess)

Text: „Guten Morgen! Das Wohnzimmerlicht ist jetzt eingeschaltet, und draußen sind es zwölf Grad bei
leichtem Regen. Soll ich die Heizung im Bad etwas höher stellen?“, Sprache `de`, Stimme `ryan`, Seed 1,
`speech tts` auf der Kommandozeile.

| Backend | Audio | Rechenzeit | RTFx | Erstes Audio |
|---|---|---|---|---|
| ROCm | 10,88 s | 6,44 s | 1,7 | 0,398 s |
| Vulkan, Lauf 1 | 10,16 s | 5,75 s | 1,8 | 0,716 s |
| Vulkan, Lauf 2 | 10,16 s | 5,62 s | 1,8 | 0,615 s |
| CPU | 10,40 s | 7,63 s | 1,4 | 0,193 s |

Der CPU-Lauf brauchte 1 min 32 s CPU-Zeit (über alle Threads) für 8,6 s Wandzeit; der ROCm-Lauf 12 s.
Die Audiolänge unterscheidet sich trotz gleichem Seed je Backend, weil die Rechenwege leicht verschieden
runden und das Modell sampelt.

### Warm: drei Sätze in einem Prozess (0.6B)

Drei kurze Sätze nacheinander im selben Prozess; ab dem zweiten ist das Modell warm, so wie in einem
laufenden Server.

| | ROCm: Audio / Zeit / RTFx / erstes Audio | Vulkan: Audio / Zeit / RTFx / erstes Audio |
|---|---|---|
| Satz 1 (kalt) | 4,80 s / 2,81 s / 1,7 / 0,217 s | 5,12 s / 3,05 s / 1,7 / 0,589 s |
| Satz 2 | 3,76 s / 2,09 s / 1,8 / 0,058 s | 3,20 s / 1,45 s / 2,2 / 0,048 s |
| Satz 3 | 3,44 s / 1,86 s / 1,8 / 0,058 s | 3,12 s / 1,63 s / 1,9 / 0,048 s |
| gesamt | 12,00 s / 6,76 s / 1,8 | 11,44 s / 6,13 s / 1,9 |

In diesen Einzelläufen lagen ROCm und Vulkan scheinbar gleichauf. Die Messreihe oben zeigt Vulkan klar
vorn.

### 0.6B gegen 1.7B (Vulkan, je ein frischer Prozess)

Gleicher Text wie oben, Seed 1, 24 Dateien.

| Modell | RTFx | Erstes Audio (kalt) |
|---|---|---|
| 0.6B | 1,8–1,9 | 0,64–0,71 s |
| 1.7B | 1,3–1,4 | 0,68–0,88 s |

### Einordnung: Zahlen des Projekts

Aus `docs/models/qwen3-tts.md` von speech.cpp: Worker, warm, Q8_0, Median aus drei Runden.

| Modell | Gerät | RTFx | Erstes Audio p50 |
|---|---|---|---|
| 0.6B | Apple M5, Metal | 3,7 | 0,029 s |
| 1.7B | Apple M5, Metal | 2,6 | 0,041 s |
| 0.6B | RTX 2080, Vulkan | 5,2 | 0,024 s |
| 1.7B | RTX 2080, Vulkan | 4,2 | 0,032 s |
| 0.6B | Radeon 890M, Vulkan (Messreihe, CLI warm, 30 Sätze) | 2,16 | 0,050 s |
| 1.7B | Radeon 890M, Vulkan (Messreihe, CLI warm, 30 Sätze) | 1,56 | 0,067 s |

Die Zahlen des Projekts sind Mediane über 20 japanische Sätze durch den Worker, diese hier gesamt bzw.
Median über 30 deutsche Sätze auf der Kommandozeile. Die Größenordnung ist vergleichbar, die Methode nicht
genau gleich. Die 890M ist mit 0.6B etwa 2,4-mal langsamer als die RTX 2080 und 1,7-mal langsamer als der
M5.

### Stimmen und Instruktionen

- CustomVoice hat neun feste Sprecher, vier davon weiblich: `serena`, `vivian` (beide zh), `sohee` (ko),
  `ono_anna` (ja). Alle sprechen Deutsch. Favorit nach Hörtest: `ono_anna`.
- **Instruktionen** (OpenAI-Feld `instructions`, bei Qwen `instruct`) beschreiben, *wie* gesprochen wird,
  nicht die Stimme selbst. Sie gehen nur mit 1.7B; das 0.6B lehnt sie ab, weil der offizielle Code sie
  dort verwirft. VoiceDesign (eine Stimme frei beschreiben) und Voice-Cloning unterstützt speech.cpp bei
  Qwen3-TTS nicht.
- Ein Tempo-Parameter fehlt; das Tempo lässt sich nur über eine Instruktion steuern.

Wirkung der Instruktionen auf die Audiolänge (1.7B, gleicher Text, Seed 1, je ein Lauf). Die Länge
schwankt auch ohne Instruktion mit dem Seed; die Tabelle zeigt eine Tendenz, keinen Beweis.

| Stimme | ohne | „zügig“ | „freundlich“ | „ruhig“ | „Nachrichten“ |
|---|---|---|---|---|---|
| serena | 10,32 s | 10,48 s | 9,68 s | 10,64 s | 9,68 s |
| vivian | 11,28 s | 10,00 s | 9,68 s | 12,24 s | 9,84 s |
| sohee | 11,28 s | 8,72 s | 8,88 s | 13,60 s | 8,40 s |
| ono_anna | 9,52 s | 8,24 s | 9,44 s | 11,36 s | 9,12 s |

0.6B ohne Instruktion zum Vergleich: serena 10,16 s, vivian 10,08 s, sohee 9,44 s, ono_anna 9,92 s.

Verwendete Instruktionen (Englisch):
- zügig: „Speak at a slightly brisker pace than usual, friendly and clear.“
- freundlich: „Speak in a warm, cheerful and friendly tone, like a helpful assistant who is happy to help.“
- ruhig: „Speak calmly and softly, slow and soothing, like reading a bedtime story.“
- Nachrichten: „Speak like a professional news anchor: neutral, crisp, confident and a bit fast.“

Beobachtung: „ruhig“ verlängert bei allen vier Stimmen, „zügig“ wirkt bei sohee (−23 %) und ono_anna (−13 %)
deutlich, bei serena gar nicht.

### Als Dienst für Home Assistant (1.7B, Vulkan, Wyoming)

`speech serve qwen3-tts-1.7b` im Container plus ein Wyoming-Shim, der PCM streamt, Stil-Tags im Text
(`[ruhig]`, `[stil: …]`) in Instruktionen übersetzt und ohne Tag den Stil nach Tageszeit wählt. Jeder
Abschnitt mit eigenem Stil ist eine eigene Anfrage.

Vom Shim gemessen, pro Anfrage an den Server:

| Satz | Audio | Zeit | RTFx | Erstes Audio |
|---|---|---|---|---|
| „Das Licht im Flur ist jetzt aus.“ (Nachrichten) | 2,64 s | 1,70 s | 1,5 | 0,088 s |
| „Alles klar, ich habe die Heizung … gestellt.“ (zügig) | 3,92 s | 2,50 s | 1,6 | 0,097 s |
| „Achtung, das Fenster … ist noch offen.“ (ernst) | 3,36 s | 2,15 s | 1,6 | 0,090 s |
| „Soll ich dich in zehn Minuten erinnern?“ (zügig) | 2,16 s | 1,41 s | 1,5 | 0,087 s |

Vom Wyoming-Client gemessen (so wie Home Assistant es sieht):

| Fall | Audio | Erstes Audio | Gesamt |
|---|---|---|---|
| Ein Text mit zwei Stilen (`[ruhig] … [fröhlich] …`) | 8,64 s | 0,184 s | 5,79 s |
| Stimmvariante `ono_anna-nachrichten`, ein Satz | 2,64 s | 0,089 s | 1,70 s |
| Gestreamter Text in 5 Chunks (150 ms Abstand), 3 Sätze | 9,44 s | 0,401 s | 6,36 s |

Beim gestreamten Fall entfällt der größte Teil der 0,4 s aufs Warten, bis der erste Satz vollständig
angekommen ist.

### Im Alltag mit Mira

Eine knappe Stunde Gespräch über das Echo Show 5 am 18.11.2026, Stimme `sohee`, Qwen3-TTS 1.7B auf
Vulkan, je Satz eine Anfrage an den Server. Im Server-Log lag das erste Audio jeder Antwort bei 84–117 ms,
der RTFx bei 1,4–1,6.

**Sprachwechsel:** Mira antwortete auf englische Fragen auf Englisch. Der Shim gibt der TTS dabei die
Sprache weiter, die Home Assistant für die Pipeline mitschickt, und wechselt sie nicht mit dem Text. Für den Sprecher klangen die englischen Antworten trotzdem richtig, ohne
deutschen Akzent; das ist ein Höreindruck, keine Messung.

**Kauderwelsch:** Eine Antwort war unverständlich, obwohl der angezeigte Text stimmte: „Ich kenne den
ganzen Text, aber ich kann dir den genauen Wortlaut auch für die weiteren Strophen aufzählen, wenn du
möchtest.“ Sie kam unmittelbar nach Antworten mit englischen Liedzeilen. Qwen3-TTS sampelt jedes Token
(Temperatur 0,9) und verrutscht dabei gelegentlich in Lautfolgen ohne Sinn. Gegengeprüft durch
Rückerkennung mit Qwen3-ASR 1.7B:

| Fall | unverständlich |
|---|---|
| Der rein deutsche Satz oben, verschiedene Seeds und Sprachangaben, mit und ohne Instruktion | 1 von 28 („Kich machini niti.“ vor dem Satz) |
| Zwei Sätze Deutsch mit Englisch, Temperatur 0,9 (Standard) | 5 von 20 |
| dieselben, Temperatur 0,6 | 6 von 20 |
| dieselben, Temperatur 0,3 | 3 von 20 |
| „Das Lied beginnt mit den Zeilen: There is lambswool …“ in zwei Anfragen geteilt, Deutsch mit `de`, Englisch mit `en` | Deutsch 0 von 5, Englisch 1 von 5 |

Typisch für gemischte Sätze ist, dass der deutsche Teil englisch ausgesprochen wird („Das Lied beginnt“
wurde als „This lead begins …“ erkannt). Die Bewertung per Rückerkennung ist bei gemischten Sätzen
unsicher, weil Qwen3-ASR dort teils übersetzt („The song begins with the lines“). Eine niedrigere
Temperatur half nicht erkennbar; Sätze nach Sprache zu teilen half.

**Vulkan ist nicht reproduzierbar:** Derselbe Text mit demselben Seed ergab im selben Prozess auf Vulkan
verschiedene Ergebnisse, bei 8 gleichen Anfragen 5 verschiedene Längen (4,08–4,96 s). Auf ROCm waren
alle 8 gleich, auf der CPU alle 5. In getrennten Prozessen war auch Vulkan gleich. Die Dokumentation von
speech.cpp sagt, dass derselbe Seed auf demselben Gerät dasselbe Audio gibt; auf der 890M mit RADV gilt
das für Vulkan nicht. Ein Live-Fehler lässt sich darum mit dem geloggten Seed nicht nachstellen. Ob die
Abweichung das Kauderwelsch häufiger macht, ist nicht untersucht.

## STT: Qwen3-ASR gegen faster-whisper

### Backends im Vergleich (Qwen3-ASR 0.6B)

Eingabe: die 10,88 s lange TTS-Ausgabe von oben, `speech asr` auf der Kommandozeile.

| Backend | Zeit | RTFx |
|---|---|---|
| ROCm | 0,927 s | 11,7 |
| Vulkan | 0,924 s | 11,8 |
| CPU | 1,221 s | 8,9 |

Erkannt (ROCm): „Guten Morgen, das Wohnzimmerlicht ist jetzt eingeschaltet, und draußen sind es zwölf Grad
bei leichtem Regen. Soll ich die Heizung im Bade etwas höher stellen?“ Einziger Fehler: „Bade“ statt „Bad“.

### Gemischte Sprache über Wyoming

Sechs Aufnahmen, fünf davon deutsch mit englischen Begriffen. Gesprochen von der Qwen3-TTS (`ono_anna`) und
auf 16 kHz gewandelt; Aufnahme 6 ist eine vorhandene Testdatei. Gemessen wie Home Assistant: Transcribe,
Audio in Chunks zu 1024 Samples, dann AudioStop; die Zeit läuft von AudioStop bis zum Transkript.

- Qwen3-ASR: Vulkan, Sprache automatisch erkannt (hat jedes Mal Deutsch erkannt).
- faster-whisper: large-v3-turbo über CTranslate2 auf ROCm, float16, Beam 1, Silero-VAD-Filter, Sprache
  fest `de`.

| Aufnahme (Länge) | Qwen3-ASR 1.7B | Qwen3-ASR 0.6B | faster-whisper |
|---|---|---|---|
| 1 (6,6 s) | „**Spielt** bitte den Song Highway to Hell von AC/DC im Wohnzimmer.“ 0,62 s | „**Spielen** bitte …“ 0,30 s | „Spiel bitte … von **ACDC** im Wohnzimmer.“ 1,12 s |
| 2 (3,4 s) | „**Setzt** ein Meeting mit dem Team für das Quarterly Review auf Freitag.“ 0,60 s | wie 1.7B, 0,23 s | „Setz ein Meeting … Quarterly Review auf Freitag.“ 0,93 s |
| 3 (4,1 s) | „Wie ist das Wetter in New York und ist der Flug nach Boston on time?“ 0,64 s | gleich, ohne „?“, 0,26 s | wie 1.7B, 0,93 s |
| 4 (4,8 s) | „Schalte das Licht in der Küche aus und starte die Playlist Chill Vibes auf Spotify.“ 0,67 s | gleich, 0,28 s | gleich, 0,98 s |
| 5 (5,8 s) | „Erinnere mich morgen um neun an das Deployment vom neuen Feature Branch.“ 0,63 s | gleich, 0,26 s | „… um **9** …“ 0,94 s |
| 6 (3,5 s) | „Im Wohnzimmer sind es dreiundzwanzig Grad, ganz gemütlich.“ 0,59 s | gleich, 0,25 s | „… sind es **23** Grad …“ 0,90 s |

| | Qwen3-ASR 1.7B | Qwen3-ASR 0.6B | faster-whisper |
|---|---|---|---|
| Zeit pro Äußerung | ~0,6 s | ~0,25 s | ~0,95 s |
| RTFx | 6–10 | 14–22 | 4–6 |
| Englische Begriffe | alle richtig | alle richtig | alle richtig, „ACDC“ statt „AC/DC“ |
| Fehler | Befehlsform: „Spielt“, „Setzt“ | „Spielen“ | keine |
| Zahlen | als Wort | als Wort | als Ziffer |

Varianten mit Qwen3-ASR 1.7B:
- Sprache fest `de` statt automatisch: gleicher Text, etwas schneller (0,47–0,60 s).
- Original 24 kHz statt 16 kHz: „Spiele“ statt „Spielt“, „23“ statt „dreiundzwanzig“, sonst gleich.

Durch die Speaker-ID-Weiche (Wyoming-Proxy mit Sprechererkennung vor der STT), Qwen3-ASR 1.7B:

| Aufnahme | STT | Sprecher-Embedding |
|---|---|---|
| 1 (6,6 s) | 616 ms | 154 ms |
| 3 (4,1 s) | 642 ms | 107 ms |

**Grenzen dieses Vergleichs:** Die Aufnahmen sind saubere, synthetische Sprache; alle drei Systeme haben die
englischen Begriffe erkannt. Das eigentliche Problem von faster-whisper mit gemischter Sprache zeigt sich
damit nicht. Dafür bräuchte es echte Mikrofonaufnahmen, gerade von Sätzen, an denen faster-whisper bisher
scheiterte. Belegt ist der Geschwindigkeitsvorteil: 1.7B braucht etwa zwei Drittel der Zeit von
faster-whisper, 0.6B etwa ein Viertel.

### Echte Aufnahmen über das Echo Show 5

**Aufbau:** 29 Äußerungen eines Sprechers über das Mikrofon eines Echo Show 5 (TECHO5, Home Assistant
Assist mit der Speaker-ID-Weiche und dem Mira-Agenten), aufgenommen am 18.11.2026 zwischen 12:31 und
12:39 Uhr. Die Gespräche waren ein Vokabeltest, ein IT-Quiz und Alltagsfragen. Jede Äußerung wurde live
von Qwen3-ASR 1.7B erkannt und als 16-kHz-WAV gespeichert. Danach liefen alle Aufnahmen ohne Last daneben
noch einmal durch Qwen3-ASR 1.7B, Qwen3-ASR 0.6B (beide Vulkan, Sprache automatisch) und faster-whisper
(large-v3-turbo, ROCm, Sprache fest `de`). Die Wahrheit hat der Sprecher bei allen Stellen festgelegt, an
denen die Systeme verschieden lagen.

**Gezählt** werden nur inhaltliche Fehler. Zahlen als Wort oder Ziffer, Satzzeichen, Groß- und
Kleinschreibung, Zusammen- oder Getrenntschreibung und „Website“ gegen „Webseite“ zählen nicht. Die 29
Äußerungen haben zusammen 155 Wörter.

| | Äußerungen mit Fehler | Wortfehler | Fehlerquote | Zeit p50 / p90 / max |
|---|---|---|---|---|
| Qwen3-ASR 1.7B | 3 von 29 | 3 | 1,9 % | 0,39 / 0,71 / 0,81 s |
| faster-whisper | 3 von 29 | 3 | 1,9 % | 0,86 / 0,96 / 1,32 s |
| Qwen3-ASR 0.6B | 6 von 29 | 7 | 4,5 % | 0,16 / 0,29 / 0,34 s |

Die Zeit läuft vom Ende der Aufnahme bis zum Text. Während der Live-Session lag Qwen3-ASR 1.7B bei 0,40 bis
0,81 s; ein Teil der Session lief parallel zur TTS-Messreihe auf derselben GPU.

Die Fehler im Einzelnen (gesagt → erkannt):

| Gesagt | Qwen3-ASR 1.7B | Qwen3-ASR 0.6B | faster-whisper |
|---|---|---|---|
| Wald. | richtig | richtig | **Bald.** |
| Eichhörnchen. | richtig | **Ichenchen** | richtig |
| Lehrer. | richtig | **Lero** | richtig |
| Oh, das war jemand am CERN. … | **(Oh fehlt)** | **Ah** … **Zern** | **Zern** |
| L1 Cache. | L eins **Cash** | L eins **Cash** | L1 **Cash** |
| Wer waren die Gründungsmitglieder der Gruppe Pink Floyd? | richtig | **Wir** waren … | richtig |
| Wie könnte ich es denn schaffen, dich zu ärgern? | **könnt** | **könnt** | richtig |

Weitere Befunde:

- **Reproduzierbar:** Die zweite Erkennung mit Qwen3-ASR 1.7B ergab bei allen 29 Äußerungen exakt den Text
  der Live-Erkennung.
- **Englisch im Satz:** „Basic input-output system“, „Random access memory“, „Pink Floyd“, „HDMI“, „Intel“,
  „IT“ und „miraassist.com“ haben alle drei Systeme erkannt. „L1 Cache“ hat keines erkannt.
- **Zahlen:** Qwen schreibt sie meist als Wort („neunzehnhundertfünfundneunzig“, „fünfzehn Uhr“), aber
  nicht immer („16 Uhr“). faster-whisper schreibt Ziffern. Für einen LLM-Agenten ist das gleichwertig; ob
  die festen Satzmuster von Home Assistant (etwa Timer) Zahlwörter verstehen, ist nicht geprüft.
- **Sprechererkennung:** Die Speaker-ID hat den Sprecher in 28 von 29 Fällen sicher zugeordnet (Score
  0,85–0,93); bei „Ja, genau das. Danke.“ war sie unsicher. Das Sprecher-Embedding kostete 83–157 ms.

### Zweite Runde: Englisch und gemischte Sätze

**Aufbau:** 14 weitere Äußerungen desselben Sprechers über das Echo Show 5, am 18.11.2026 zwischen 12:45
und 12:57 Uhr. Der Prompt des Mira-Agenten verlangte inzwischen, in der Sprache zu antworten, in der er
angesprochen wird. Der Sprecher wechselte zwischen Deutsch, Englisch und Sätzen mit beidem. Auswertung wie
oben, alle drei Systeme ohne Last daneben.

Die englischen Äußerungen:

| Qwen3-ASR 1.7B | faster-whisper (Sprache fest `de`) |
|---|---|
| What time is it? | **Was ist das?** |
| I see that you now can also talk English with me. Is this a new feature? | **Ich sehe, dass Sie jetzt auch Englisch mit mir sprechen können. Ist das eine neue Funktion?** |
| Can we play a quiz, but really a simple one and just three questions? Okay. | **Kann ich ein Quiz spielen? Aber wirklich eine einfach eine, nur drei Fragen. Okay?** |
| It's in Africa. | **Es ist in Afrika.** |
| Can you tell a little bit about you? | **Kannst du dir ein bisschen über dich erzählen?** |
| An ocean. | An ocean. |

**faster-whisper übersetzt Englisch ins Deutsche**, weil seine Sprache fest auf `de` steht: Fünf von sechs
englischen Äußerungen kamen als deutscher Text heraus, eine davon zudem falsch („What time is it?“ wurde
„Was ist das?“). Für einen Agenten, der in der Sprache des Sprechers antworten soll, ist das ein harter
Fehler: Er sieht nie, dass Englisch gesprochen wurde. Qwen3-ASR hat alle sechs im Original erkannt, auch
Qwen3-ASR 0.6B. Die automatische Spracherkennung meldete bei diesen Sätzen `en`.

Die gemischten Äußerungen:

| Gesagt (laut Qwen3-ASR 1.7B) | Ergebnis |
|---|---|
| Ich verstehe die Zeilen nicht aus dem Genesis-Lied Carpet Crawler. Es fängt an mit There is lambswool under my naked feet. The wool is soft and warm. | alle drei Systeme gleich |
| Kannst du mir auf Deutsch übersetzen, was "attitude" heißt? | alle drei gleich |
| Ein Gemüse, a vegetable. | faster-whisper: „Aha, ein Gemüse, a vegetable.“; Qwen3-ASR 1.7B lässt „Aha“ weg |
| Ich suche den Anfang von dem Lied der Carpet Crawlers von Genesis. Kennst du den Text? | 1.7B und faster-whisper gleich; 0.6B „The Carpet Crawlers“ |

Den 11,6 s langen Genesis-Satz (Deutsch mit zwei englischen Liedzeilen) hat Qwen3-ASR richtig erkannt,
obwohl seine Spracherkennung ihn als `en` einstufte: Die Sprache steuert nur, sie zwingt nicht den ganzen
Text in eine Sprache. faster-whisper hat diesen Satz ebenfalls richtig erkannt; gemischte Sätze mit
überwiegend Deutsch waren für es kein Problem, ganze englische Sätze schon.

Was der Sprecher bei „Ein Gemüse“ (mit „Aha“?) und „der/The Carpet Crawlers“ wirklich gesagt hat, ist nicht
geklärt; diese Stellen sind in keiner Fehlerquote gezählt.

**Zeiten über alle 43 Äußerungen** (210,6 s Audio, im Mittel 4,9 s je Äußerung):

| | p50 | p90 | max |
|---|---|---|---|
| Qwen3-ASR 1.7B | 0,48 s | 0,73 s | 1,34 s |
| Qwen3-ASR 0.6B | 0,21 s | 0,30 s | 0,58 s |
| faster-whisper | 0,90 s | 1,00 s | 1,21 s |

Das Maximum von Qwen3-ASR 1.7B ist der 11,6-s-Satz; faster-whisper brauchte für ihn 1,19 s. Auch diese
zweite Erkennung mit Qwen3-ASR 1.7B ergab bei allen 43 Äußerungen exakt den Live-Text.

**Fazit STT:** Auf deutscher Sprache ist Qwen3-ASR 1.7B gleich genau wie faster-whisper (je 3 Wortfehler auf
155 Wörter) und knapp doppelt so schnell (p50 0,48 s gegen 0,90 s). Seine Fehler verändern die Bedeutung
nicht (ein fehlendes „Oh“ oder „Aha“, „könnt“ statt „könnte“); die von faster-whisper tun es („Bald“ statt
„Wald“, „Zern“ statt „CERN“). Den Ausschlag gibt Englisch: faster-whisper mit fester Sprache übersetzt
ganze englische Sätze ins Deutsche, Qwen3-ASR mit automatischer Spracherkennung erkennt sie im Original und
bleibt bei deutschen Sätzen genauso gut. Für einen zweisprachigen Haushalt ist das der wesentliche
Unterschied. Qwen3-ASR 0.6B ist am schnellsten, verfehlt aber einzelne deutsche Wörter deutlich öfter
(7 Wortfehler auf 155 Wörter).

Nicht geprüft wurde faster-whisper mit automatischer Spracherkennung statt fester Sprache; ob es dann
Englisch behält und Deutsch genauso gut erkennt, ist offen.

## Was sich nicht messen ließ oder offen blieb

- Ein Vergleich mit der vorher genutzten Python-Variante von Qwen3-TTS (PyTorch auf ROCm) wurde in dieser
  Sitzung nicht gemessen; überliefert ist nur der Eindruck „viel zu langsam“.
- Keine Speichermessung (Spitzenspeicher, VRAM).
- STT: Die Fehlerquoten auf Deutsch beruhen auf 29 echten Äußerungen (155 Wörter) eines Sprechers. Das
  reicht für eine Tendenz, nicht für einen belastbaren Unterschied zwischen 1,9 % und 1,9 %. Der Befund zu
  Englisch (5 von 6 übersetzt) ist dagegen eindeutig, aber ebenfalls von einem Sprecher.
- STT: faster-whisper mit automatischer Spracherkennung wurde nicht getestet.
- TTS: Wie oft Kauderwelsch im Alltag vorkommt, beruht auf wenigen Dutzend Sätzen und einer Rückerkennung,
  die bei gemischten Sätzen unsicher ist.
- TTS: keine Bewertung der Sprachqualität (etwa Zeichenfehler per Rückerkennung, wie es die Projektdoku
  macht), nur Hörtest.
- Qwen3-TTS 1.7B: Ladezeit und Download nicht gemessen.
