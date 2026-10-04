# Wytyczne dobrej prezentacji na hackathon

Opracowane na podstawie poradnika Y Combinator, oficjalnych zasad ETHGlobal (jednego z największych hackathonów na świecie) oraz uwag jurorów z hackathonów.

---

## Najważniejsza różnica: YC Demo Day to nie hackathon

Poradnik YC pisany jest pod inwestorów, którzy oglądają dziesiątki startupów. Celem nie jest przekonanie ich od razu, tylko zaintrygowanie na tyle, żeby chcieli się spotkać. YC zauważa też, że demo rzadko sprawdza się na Demo Day, bo firmy mają już klientów i trakcję.

Na hackathonie jest odwrotnie: nie masz trakcji, więc **działające demo jest Twoją trakcją**.

- Z YC bierz: strukturę opowieści i zasady mówienia.
- Z hackathonów bierz: układ czasowy i demo jako oś pitchu.

---

## Czego uczy Y Combinator

1. **Wybierz 3–4 „kręgosłupy" historii.** Słuchacze zapamiętują najwyżej 3–4 kluczowe punkty, zwłaszcza po wielu prezentacjach. Pytania pomocnicze od YC:
   - Co budujecie i dla kogo?
   - Dlaczego nikt tego wcześniej nie zrobił?
   - Dlaczego to trudne?
   - Dlaczego to okazja, której nie wolno przegapić?
2. **Od razu powiedz, co robicie, prostym językiem.** „Dostarczamy zakupy do domu" jest lepsze niż „AI-owy resolver potrzeb zakupowych". Najczęstszy błąd to odkładanie wyjaśnienia produktu na późno.
3. **Nie chowaj najmocniejszego argumentu.** Jeśli masz imponującą liczbę, pokaż ją na początku, nie na końcu.
4. **Slajdy wspierają opowieść, nie odwrotnie.**
   - Jeden slajd = jeden punkt.
   - Obraz zamiast tekstu, jeśli się da.
   - Powyżej ok. 7 słów na slajd to zwykle za dużo.
   - Duża czcionka, ważny tekst u góry slajdu.
   - Publiczność nie czyta i nie słucha jednocześnie.
5. **Mów wolniej, niż Ci się wydaje.** YC radzi mówić wręcz nienaturalnie wolno, robić pauzy i patrzeć na publiczność, a nie na ekran. Paul Graham dodaje regułę aktorów: jeśli czujesz, że mówisz za wolno, tempo jest prawdopodobnie dobre.
6. **Jedna osoba prezentuje.** YC odradza przełączanie się między mówcami. Wybierz tego, kto mówi najlepiej, niezależnie od roli w zespole.
7. **Ćwicz.** To według YC jedyna technika przygotowania, która naprawdę ma znaczenie. Nagrywaj siebie i proś o szczerą krytykę.
8. **Zakończ mocno.** Powiedz wprost, co publiczność ma zapamiętać, najlepiej wymieniając te 3–4 kręgosłupy.

### Błędy do uniknięcia (YC)

- Żargon, marketingowy bełkot, zbyt skomplikowane opisy.
- Przesada i nieprawda (YC nazywa to błędem fatalnym).
- Skomplikowane wykresy.
- Wideo na slajdach.
- Patrzenie na slajdy zamiast na publiczność.
- Zbyt dużo słów i zbyt szybkie tempo.
- Brak pauz.
- Znudzony lub wrogi ton, brak pasji.

---

## Czego uczy ETHGlobal

### Finały
- **Format:** 7 minut na zespół: **4 minuty demo + 3 minuty pytań** od jury.
- **Typowe pytania:** skąd pomysł, jakie narzędzia i dlaczego, jakie problemy rozwiązaliście.

### Pięć kryteriów jury
1. **Technicality**: złożoność problemu i dopracowanie rozwiązania
2. **Originality**: nowy pomysł lub kreatywne podejście do znanego problemu
3. **Practicality**: kompletność i funkcjonalność, czy dałoby się z tego korzystać już dziś
4. **Usability (UI/UX/DX)**: intuicyjność i łatwość użycia
5. **WOW Factor**: czy projekt zostaje w pamięci

### Wideo demo (2–4 minuty)
- Wstęp maksymalnie 20 sekund.
- Mów wyraźnie, nie za szybko.
- Dobry mikrofon i brak echa.
- Pomijaj nudne czekanie (wideo można zmontować).
- Slajdy podsumowujące: maksymalnie 4 punkty na slajd.

### Czego nie robić w nagraniu
- Rozdzielczość poniżej 720p.
- Przekraczanie 4 minut lub przyspieszanie wideo, żeby się zmieścić.
- Muzyka z tekstem zamiast mówienia.
- Nagrywanie telefonem.
- Syntezator mowy / głos generowany przez AI.

### Przejrzystość pracy
- Repozytorium z historią commitów (duże pojedyncze commity mogą skutkować dyskwalifikacją).
- Jasne rozdzielenie, co powstało podczas hackathonu, a co jest z gotowych bibliotek.
- Udokumentowane użycie narzędzi AI.

---

## Co mówią jurorzy z hackathonów

- Silny projekt z mętnym demo przegrywa z prostszym, który jury rozumie.
- Dobre demo jest ważniejsze niż najczystszy kod i architektura.
- **Demo ma być osią pitchu.** Jeśli się nie mieści w czasie, tnij funkcje, a nie tempo.
- Napisz skrypt demo (ok. 90 sekund) zanim napiszesz sensowną ilość kodu. Skrypt zawiera moment „aha", który jury ma zapamiętać.
- Demo na localhost z niestabilnym API to przepis na porażkę przed jury.
- Miej nagrane demo awaryjne i zachowaj spokój, jeśli coś się wysypie.
- Pytania jury często trwają tyle co demo, więc przewidź je wcześniej.
- Przeczytaj kryteria oceniania i problem/temat hackathonu przed rozpoczęciem pracy.
- Jury wyczuwa entuzjazm i to, czy rozumiesz własny kod.

---

## Szkielet 3-minutowego pitchu (synteza)

| Czas | Co |
|---|---|
| 0:00–0:20 | **Problem:** jedno zdanie i jedna liczba |
| 0:20–0:40 | **Rozwiązanie:** co zbudowaliście, jednym zdaniem (bez „jak") |
| 0:40–2:30 | **Live demo:** otwarcie aplikacji, główna akcja użytkownika, wynik |
| 2:30–3:00 | **Zakończenie:** dlaczego Wy, co dalej, 2–3 rzeczy do zapamiętania |

> Podział czasowy pochodzi z jednego poradnika hackathonowego. Traktuj go jako punkt wyjścia i dopasuj do limitu na swoim wydarzeniu (np. ETHGlobal: 4 min demo + 3 min Q&A).

---

## Checklista na dzień prezentacji

- [ ] Przeczytałem kryteria oceniania i pitch jest ułożony pod nie
- [ ] Pokazuję tylko to, co działa (żadnych połowicznych funkcji)
- [ ] Przećwiczyłem na głos z zegarkiem co najmniej 3–5 razy
- [ ] Mam backup: nagrane demo i zrzuty ekranu
- [ ] Wybrany jest jeden mówca, rozpisane są odpowiedzi na pytania
- [ ] Demo działa na docelowym urządzeniu (nie tylko na localhost)
- [ ] Zakończenie powtarza 2–3 rzeczy, które jury ma zapamiętać
- [ ] README i repo są czytelne dla jurorów, którzy nie zobaczą demo na żywo

---

## Źródła

- Y Combinator, *A Guide to Demo Day Presentations* (Geoff Ralston): https://www.ycombinator.com/blog/guide-to-demo-day-pitches/
- Paul Graham, *How to Present to Investors*: https://paulgraham.com/investors.html
- ETHGlobal Cannes, zasady, kryteria i wytyczne wideo: https://ethglobal.com/events/cannes/info/details
- JetBrains, *How to Win a Hackathon: Notes From the Judging Table*: https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table/
- HackerEarth, *How to Win a Hackathon: 10 Tips From 500+ Events*: https://www.hackerearth.com/blog/10-tips-win-hackathon
- AngelHack, *10 tips to help you rock your next hackathon demo*: https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/
- Reskilll, *Hackathon Demo and Presentation Tips: How to Pitch in 3 Minutes and Win*: https://blogs.reskilll.com/hackathon-demo-presentation-tips-pitch-3-minutes-win-2026/
