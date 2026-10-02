# Întrebări frecvente

- [Cum instalez eToll?](#cum-instalez-etoll)
- [Ce senzori sunt creați?](#ce-senzori-sunt-creați)
- [De ce un senzor afișează `Unknown`?](#de-ce-un-senzor-afișează-unknown)
- [De ce Restanțe treceri pod este întotdeauna `Unknown`?](#de-ce-restanțe-treceri-pod-este-întotdeauna-unknown)
- [Ce înseamnă starea senzorului Rovinietă activă?](#ce-înseamnă-starea-senzorului-rovinietă-activă)
- [Cum modific intervalul de actualizare?](#cum-modific-intervalul-de-actualizare)
- [Ce se schimbă față de vechea integrare?](#ce-se-schimbă-față-de-vechea-integrare)
- [Ce fac dacă autentificarea eșuează?](#ce-fac-dacă-autentificarea-eșuează)

## Cum instalez eToll?

În HACS, adaugă [repository-ul vladurash/etollro_ha](https://github.com/vladurash/etollro_ha) ca repository personalizat de tip **Integration**, instalează **eToll** și repornește Home Assistant. Alternativ, copiază directorul `etoll/` în `custom_components/etoll/` și repornește Home Assistant.

Apoi deschide **Settings → Devices & services → Add integration**, caută **eToll** și introdu numele de utilizator și parola contului tău eToll.

## Ce senzori sunt creați?

Este creat un senzor de cont și un set de senzori pentru fiecare vehicul de tip autoturism returnat de portal:

| Senzor | Valoare |
| --- | --- |
| **Date utilizator** | `Conectat` sau `nespecificat`; atributul `username` conține contul configurat. |
| **Rovinietă activă (număr)** | `Da`, `Nu` sau `Necunoscut`, în funcție de data de expirare disponibilă. |
| **Restanțe treceri pod (număr)** | Senzor legacy; `Unknown` și dezactivat, deoarece nu există o rută confirmată pentru detectarea restanțelor. |
| **Treceri pod (număr)** | Senzor legacy; treceri confirmate când sunt returnate. Dacă valoarea este `Unknown`, Home Assistant îl dezactivează și îi păstrează intrarea în registru. |
| **Sold peaje neexpirate (număr)** | Senzor legacy; soldul disponibil sau `Unknown`. Când valoarea este `Unknown`, Home Assistant îl dezactivează și îi păstrează intrarea în registru. |
| **Raport tranzacții** | Numărul facturilor și suma totală când portalul returnează facturi, altfel `Unknown`. |

## De ce un senzor afișează `Unknown`?

Înseamnă că portalul nu a returnat date pentru acel tip de informație. Senzorul **Raport tranzacții** rămâne activ și afișează `Unknown` când nu există facturi. La inițializarea sau reîncărcarea integrării, senzorii legacy pentru restanțe, treceri și sold peaje sunt dezactivați în registrul Home Assistant dacă valoarea lor este `Unknown`; integrarea le păstrează ID-urile pentru compatibilitate.

Erorile din cererile opționale pentru treceri de pod și facturi sunt înregistrate în log, dar nu ar trebui să împiedice actualizarea datelor vehiculului și rovinietei.

## De ce Restanțe treceri pod este întotdeauna `Unknown`?

Integrarea nu are încă un endpoint eToll confirmat care să identifice trecerile detectate și neachitate. Un răspuns gol de la `/api/tolls` indică doar că nu au fost returnate înregistrări de toll pentru filtrul folosit; nu dovedește că există sau nu există restanțe. Senzorul păstrează `Unknown` până când există o sursă API verificată pentru această stare.

## Ce înseamnă starea senzorului Rovinietă activă?

- **`Da`** — data expirării rovinietei curente este în viitor.
- **`Nu`** — data expirării este trecută.
- **`Necunoscut`** — portalul nu a furnizat o dată de expirare care să poată fi verificată.

Senzorul include atributele vehiculului și ale rovinietei atunci când portalul le returnează, inclusiv numărul de înmatriculare, data expirării, categoria și indicatorul `isValid`.

## Cum modific intervalul de actualizare?

Deschide **Settings → Devices & services → eToll → Configure → Settings** și alege intervalul în secunde. Valoarea implicită este 86.400 de secunde (24 de ore); sunt acceptate valori între 300 și 86.400 de secunde.

## Ce se schimbă față de vechea integrare?

Componenta și domeniul Home Assistant au fost redenumite din `etoll` în `etoll`; versiunea curentă este **1.0.0**. Home Assistant tratează domeniul nou ca pe o integrare separată și nu migrează automat vechile intrări sau ID-uri din registrul entităților.

Pentru trecere, elimină intrarea veche, instalează componenta în `custom_components/etoll/`, repornește Home Assistant și adaugă din nou **eToll**. Verifică automatizările și dashboard-urile, deoarece entitățile noi folosesc de regulă prefixul `sensor.etoll_`.

## Ce fac dacă autentificarea eșuează?

Verifică dacă te poți autentifica în portalul eToll cu aceleași date. Dacă parola s-a schimbat, folosește **Reconfigure** pentru intrarea eToll sau elimină și adaugă din nou integrarea. Consultă logurile Home Assistant pentru detaliile erorii.

Pentru depanare detaliată, activează logarea pentru `custom_components.etoll` conform instrucțiunilor din [README.md](README.md#troubleshooting).
