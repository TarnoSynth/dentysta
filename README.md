# Przychodnia dentystyczna

Aplikacja rezerwacji wizyt. Python, Flask, MySQL. Czas kliniki to czas lokalny komputera, na którym działa serwer.

## Uruchomienie

W katalogu projektu:

```powershell
docker compose up --build
```

To podnosi aplikację i MySQL. Nic nie trzeba instalować osobno. Aplikacja jest pod adresem http://127.0.0.1:5000

Przy pierwszym starcie baza dostaje dane demo. Zostają one między restartami. Czyszczenie razem z bazą: `docker compose down -v`.

## Konta demo

- Administrator: `admin@klinika.local` / `Admin12345`
- Pacjent: `jan@example.com` / `Pacjent123`
- Pacjent: `ewa@example.com` / `Pacjent123`

Hasło w `.env` musi pasować do konta MySQL. W przykładzie użytkownik `root` ma hasło `dental`.
