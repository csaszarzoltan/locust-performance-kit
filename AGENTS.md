# MiMo Code - Fejlesztési szabályok

## Követendő szabályok minden módosításnál:

1. **Mindig először teszteket készíts**
   - Új funkció előtt írj tesztet
   - A tesztek elsőként futnak le

2. **Bug javítás szabálya**
   - Bug felfedezése → először reprodukáló teszt
   - Csak ezután javítsd a hibát
   - Futasd le a tesztet, hogy igazold a javítást

3. **Fejlesztés befejezése**
   - Csak akkor fejezd be, ha minden teszt zöld
   - Ne hagyd egy fél beavatkozást

4. **Vizionális tesztek**
   - Készíts képernyőfotókat a felületekről
   - Dokumentáld a UI állapotokat
   - Rögzítsd az elvárt és aktuális viselkedést

5. **Egyediség**
   - Egy funkciót csak egyszer fejlessz le
   - Kerüld a duplikálást

6. **Dokumentáció frissítése**
   - Minden fejlesztés után frissítsd a dokumentumokat
   - Fejlesztési és felhasználói dokumentációkat tartandó naprakészen

## Projekt struktúra:

```
src/locust_templates/ - Locust sablonok
tests/ - Teljes test suite
docs/ - Dokumentáció (AppDynamics, Prometheus, Wily)
examples/ - Működő példák
```

## Munka sorrendje:
1. Olvasd el ezt a dokumentumot
2. Írj teszteket a következő funkcióhoz/ javításhoz
3. Implementáld a funkciót/javítást
4. Futtasd a teszteket: `pytest`
5. Csak zöld esetén commitolj

## Kötelező befejező lépés minden fejlesztés után
1. `git status` és `git diff` ellenőrzése.
2. Ha vannak változtatások, commit és push a `main` branchre.
3. Ha van releváns verzióemelés, frissítsd a tag-et is.

