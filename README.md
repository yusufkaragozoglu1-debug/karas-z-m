# Kararsızım

Topluluğa soru sor, oyları topla. Django tabanlı anket uygulaması. Şartname ve mimari notları: [CLAUDE.md](CLAUDE.md).

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

## Ortam değişkenleri

| Değişken | Açıklama |
|---|---|
| `DJANGO_DEBUG` | Varsayılan `False`. Yerelde `True`. |
| `DJANGO_SECRET_KEY` | `DEBUG=False` iken zorunlu. |
| `DATABASE_URL` | Boşsa SQLite. Doluysa Postgres (Supabase). |
| `ALLOWED_HOSTS` | Virgülle ayrılmış ek adresler (özel alan adı). `.vercel.app` otomatik eklenir. |
| `CSRF_TRUSTED_ORIGINS` | Özel alan adı için, ör. `https://ornek.com`. `https://*.vercel.app` otomatik eklenir. |

Gizli değer üretmek için:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(60))"
```

Gerçek değerleri (parola, secret key, bağlantı adresi) **asla** commit'leme; yerelde `.env.local`, canlıda Vercel ortam değişkenleri kullan.

## Supabase (Postgres) kurulumu

1. Supabase'de yeni proje oluştur, veritabanı parolasını not al.
2. Panelde **Connect** bölümünden iki adresi kopyala:
   - **Session pooler** (port **5432**): yerelden migration için.
   - **Transaction pooler** (port **6543**): Vercel'de uygulama için.
3. Yerelde `.env.local` dosyası oluştur (git'e girmez) ve Session pooler adresini yaz:

   ```
   DJANGO_DEBUG=True
   DATABASE_URL=postgresql://postgres.<proje-ref>:<PAROLA>@aws-0-<bölge>.pooler.supabase.com:5432/postgres
   ```

4. Tabloları oluştur ve yönetici hesabını aç:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

   > Migration'lar **transaction pooler (6543) üzerinden çalıştırılmamalı**; yalnızca Session pooler (5432) ile çalıştır.

5. Çalıştırdıktan sonra `.env.local` içindeki `DATABASE_URL` satırını sil veya yorum yap; yoksa yerel geliştirme de canlı veritabanına bağlanır.

### Supabase güvenliği (önemli)

Django tabloları `public` şemasındadır ve Supabase'in Data API'si (PostgREST) bu şemayı dışarı açabilir. İki seçenek var:

- **Seçenek A — Data API'yi kapat:** Supabase panelinde *Project Settings → Data API* bölümünden API'yi devre dışı bırak. Django doğrudan Postgres'e bağlandığı için etkilenmez.
- **Seçenek B — Politikasız RLS aç (önerilen, ek güvence):** Tüm tablolarda Row Level Security'yi politika yazmadan etkinleştirirsen `anon` ve `authenticated` rolleri hiçbir satıra erişemez. Django `postgres` rolüyle bağlandığı için RLS'yi atlar ve çalışmaya devam eder.
  1. Supabase **SQL Editor**'ı aç.
  2. [scripts/supabase_enable_rls.sql](scripts/supabase_enable_rls.sql) içeriğini yapıştırıp çalıştır.
  3. Sonuç tablosunda her satırda `rowsecurity = true` olmalı; **Security Advisor** RLS uyarısı vermemeli.

  **Yeni migration yeni tablo getirirse betiği tekrar çalıştır.**

## Vercel'e deploy

Vercel, Django'yu otomatik algılar (`manage.py` kökte, `WSGI_APPLICATION = config.wsgi.application`). Python sürümü [.python-version](.python-version) ile 3.12'ye sabitlenmiştir. `vercel.json` gerekmez; statik dosyalar WhiteNoise ile sunulur (`collectstatic` çalışmasa bile `static/` klasöründen servis edilir).

1. Kodu GitHub'a gönder.
2. Vercel'de **Add New → Project** ile GitHub reposunu içe aktar. Framework otomatik "Django" algılanır.
3. **Environment Variables** bölümüne ekle (Production):
   - `DJANGO_SECRET_KEY` = yukarıdaki komutla ürettiğin değer
   - `DATABASE_URL` = Supabase **Transaction pooler** (port **6543**) adresi
   - `DJANGO_DEBUG` = `False` (veya hiç ekleme)
4. **Deploy**'a bas.
5. Deploy sonrası kontrol:
   - `https://<proje>.vercel.app` açılıyor mu, CSS/JS yükleniyor mu?
   - Kayıt ol, giriş yap, anket oluştur, gizli pencereden oy ver.
   - Supabase **Table Editor**'da `accounts_user`, `polls_poll`, `polls_option`, `polls_vote` tabloları var mı?
   - Vercel **Logs** bölümünde hata yok mu?

Özel alan adı kullanırsan `ALLOWED_HOSTS` ve `CSRF_TRUSTED_ORIGINS` değişkenlerine ekle.

### `check --deploy` notları

```powershell
$env:DJANGO_DEBUG="False"; $env:DJANGO_SECRET_KEY="<uzun-rastgele-değer>"; $env:ALLOWED_HOSTS="ornek.vercel.app"
python manage.py check --deploy
```

Geriye kalan iki uyarı bilerek bırakıldı:

- `security.W005` (`SECURE_HSTS_INCLUDE_SUBDOMAINS`): `*.vercel.app` ortak bir alan adıdır; alt alan adlarını kapsayan HSTS burada anlamsız. Özel alan adına geçince değerlendirilebilir.
- `security.W021` (`SECURE_HSTS_PRELOAD`): Preload listesi geri alınması zor bir taahhüttür; prototip için gerekmiyor.

## Bilinen sınırlamalar

- Ziyaretçi oyları tarayıcı çerezine bağlıdır; çerez silinirse (veya gizli pencerede) tekrar oy verilebilir.
- Yerelde Python 3.15, Vercel'de Python 3.12 kullanılır.
