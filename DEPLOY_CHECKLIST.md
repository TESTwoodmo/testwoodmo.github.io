# WOODMO – Live-Rollout

- [ ] Live, V2 und WOODMO TEST verwenden unterschiedliche Supabase-Projekte. Prüfe die Zieladressen beider Builds.
- [ ] Das Banner WOODMO TEST erscheint ausschließlich im Test-Build.
- [ ] Der aktuell veröffentlichte Live-Commit ist als Rollback-Punkt markiert. Der freigegebene Stand enthält nur Programmcode und Webdateien.
- [ ] Deployment und Rollback führen keine Datenimporte, Migrationen oder Resets aus. Live-Buchungen, offene Kassen, Journale und Tagesabschlüsse bleiben erhalten.
- [ ] Nach dem Live-Rollout Versionsanzeige, Login und Artikelansicht prüfen. Keine Testbuchung auslösen.

Der Workflow-Entwurf unter `release-draft/deploy-pages.yml` bleibt bis zur Freigabe inaktiv. Notfall-Rollback: In GitHub Actions den Modus `rollback` und den im letzten Live-Lauf angezeigten `woodmo-live-before-*`-Tag wählen. Die Auswahl startet den Vorgang, die Veröffentlichung benötigt die Laufzeit des Builds und von GitHub Pages.
