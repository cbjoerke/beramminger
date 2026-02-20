# Beramminger Scraper

Automatisk scraper som henter berammingsdata fra domstol.no og lagrer dem i database.

## Funksjonalitet

- Henter daglige beramminger fra domstol.no API
- Sjekker om beramminger allerede eksisterer i databasen
- Henter tilleggsinformasjon for nye beramminger
- Lagrer data i MongoDB Atlas
- Kjører automatisk hver dag kl. 20:00 UTC via GitHub Actions