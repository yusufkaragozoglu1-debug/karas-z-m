# Kararsızım

Topluluğa soru sor, oyları topla. Django tabanlı anket uygulaması. Şartname: [CLAUDE.md](CLAUDE.md).

## Yerel kurulum (Windows)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # sonra .env içinde DJANGO_DEBUG=True yap
python manage.py migrate
python manage.py createsuperuser   # e-posta + kullanıcı adı + parola sorar
python manage.py runserver
```

Uygulama: http://127.0.0.1:8000 — Admin: http://127.0.0.1:8000/admin/

## Testler

```powershell
python manage.py test
```

## Notlar

- `DJANGO_DEBUG` varsayılan olarak `False`'tur; yerelde `.env` içinde `True` yapılmalıdır.
- `DATABASE_URL` boşsa SQLite (`db.sqlite3`) kullanılır.
- Yerelde Python 3.15, Vercel'de Python 3.12 hedeflenir (Aşama 6).
