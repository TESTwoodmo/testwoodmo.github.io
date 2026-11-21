# WOODMO – Live-Rollout

- [ ] `WoodMo_V3.0` verwendet das Live-Projekt. `TESTwoodmo` verwendet seine isolierte Testdatenbank. Prüfe die URLs in beiden Builds.
- [ ] Der Live-Build zeigt kein WOODMO-TEST-Banner. Der Test-Build zeigt es durchgehend.
- [ ] Der freigegebene Diff enthält ausschließlich Frontend und Programmlogik. Er enthält keine Datendateien, Seeds, Migrationen oder Sync-Artefakte.
- [ ] Der Live-Workflow veröffentlicht ausschließlich Webdateien. Live-Buchungen, Journale und Tagesabschlüsse bleiben unangetastet.
- [ ] Nach dem Deployment Live-Login und Artikelansicht prüfen. Keine Testbuchung auslösen.
