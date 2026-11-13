# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Kararsızım: Django anket uygulaması (Türkçe arayüz, İngilizce kod). Aşama aşama geliştiriliyor; aşama promptları `docs/Karasızım Porje.md` içinde ve bu dosyadaki **bölüm numaralarına atıf yapar — numaraları değiştirme**. Aşama durumu bölüm 13'te.

## Komutlar (Windows, proje kökünde)

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py runserver                       # yerelde .env içinde DJANGO_DEBUG=True olmalı
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test                            # tümü
python manage.py test polls.tests.test_voting.JsonVoteTests.test_success_payload   # tek test
```

`python scripts/run_prodlike.py` siteyi DEBUG=False + Transaction pooler (6543) ile `http://localhost:8000`'de çalıştırır (`.env.local`'in yorum satırı Vercel değerlerini okur). `manage.py test` `DATABASE_URL` tanımlı olsa bile SQLite test veritabanı kullanır (settings.py'de korunuyor); diğer komutlar `.env.local`'deki canlı Supabase veritabanına bağlanır. Lint/format aracı yapılandırılmamış. `DJANGO_DEBUG` varsayılanı `False` (ve `DJANGO_SECRET_KEY` zorunlu); yerel `.env` (git'e girmez) `DJANGO_DEBUG=True` içerir. Testler sırasında "staticfiles dizini yok" uyarısı zararsızdır.

## Mimari (birden çok dosyayı okumayı gerektiren noktalar)

- **Oy mantığı `polls/services.py` içinde**, view'larda değil. `cast_vote` sırayla kapalı → geçersiz seçenek → zaten oy verilmiş kontrolü yapar, `VoteError` alt sınıfları (`PollClosed` 403, `InvalidOption` 400, `AlreadyVoted` 409) hem mesajı hem HTTP kodunu taşır; `polls/views.py:poll_vote` bunları ya `messages`+redirect ya da JSON'a (`Accept: application/json`) çevirir. Race durumu `Vote` üzerindeki koşullu `UniqueConstraint`'ler + `IntegrityError` → `AlreadyVoted` ile çözülür.
- **Oy kimliği**: üye oyu `user` ile, ziyaretçi oyu imzalı `kararsizim_voter` çerezindeki token ile (`polls/voter.py`) saklanır; ikisi aynı satırda tutulmaz. `has_voted`/`get_user_vote`/`voted_poll_ids` ikisini birden (`user` VEYA token) kontrol eder — ziyaretçi oy verip sonra giriş yaparsa tekrar oy veremez.
- **Sonuç görünürlüğü** `poll_detail` içinde karar verilir: yazar, kapalı anket veya oy vermiş olan sonucu görür; oy formu ise anket açıkken ve kullanıcı oy vermemişken herkese (yazar dahil) gösterilir — yazar sonuçların altında "Sen de oy ver" formunu görür. `get_results` tek sorguda `annotate` ile sayı/yüzde/`is_leading` üretir; aynı dict yapısı hem `_results.html` şablonuna hem JSON yanıtına gider (şema bölüm 8).
- **N+1 yasağı**: liste/anketlerim `Poll` sorgusunu `_annotated_polls()` ile paylaşır; sayfadaki "oy verdin" bilgisi tek sorguyla gelir. `assertNumQueries` benzeri testler (anket sayısı artınca sorgu sayısı sabit) var — yeni sorgu eklerken bozma.
- **Kullanıcı**: `accounts.User` e-posta ile girer (`USERNAME_FIELD="email"`), e-posta `save()` ve manager'da küçük harfe çevrilir, kullanıcı adı `Lower("username")` kısıtıyla iexact benzersizdir. E-posta hiçbir şablonda/JSON'da gösterilmez (testle korunuyor).
- **Ayarlar** (`config/settings.py`): `.env` sonra `.env.local` yüklenir; `DATABASE_URL` yoksa SQLite, varsa Postgres (`CONN_MAX_AGE=0`, server-side cursor kapalı, `sslmode=require`). Üretim güvenlik ayarları `DEBUG=False` iken devreye girer; `VOTER_COOKIE_SECURE = not DEBUG`.
- **Rate limit** (`config/ratelimit.py`): `@rate_limit(name, limit, window, by="ip"|"user")` dekoratörü kayıt/giriş/oy/anket oluşturmada; sabit pencere, sayaçlar Django cache'inde (üretimde `DatabaseCache` → `django_cache` tablosu, DEBUG/test'te locmem). Cache hata verirse isteği engellemez. `RATELIMIT_ENABLED` testlerde kapalıdır; açmak için `@override_settings(RATELIMIT_ENABLED=True)` (bkz. `accounts/tests/test_ratelimit.py`). Kayıt formunda gizli `website` honeypot alanı var.
- **Frontend**: tek `static/css/main.css` ve `static/js/main.js`, framework yok. JS yalnızca ilerleyen geliştirme (Aşama 5); JS kapalıyken her akış çalışmalı. Metinler `textContent` ile basılır.
- Python yerelde 3.15, Vercel'de 3.12 hedefleniyor; her iki sürümde çalışan bağımlılıklar seç.
- Git: proje klasörünün **kendi** deposu var (`origin` = https://github.com/yusufkaragozoglu1-debug/karas-z-m, dal `main`). `.claude/` klasörü bilerek takipsiz/commit dışı bırakılır (yerel önizleme ayarı). Ana dizindeki (`C:\Users\ASUS`) eski depo ayrı bir şeydir ve `MyTestProject` uzak deposuna bağlıdır; ona dokunma.

---

# Proje Şartnamesi

> `docs/Karasızım Porje.md` içindeki aşama promptlarından türetildi.

## 1. Amaç
"Kararsız mı kaldın? Topluluğa sor!" Herkes 2–5 seçenekli anket açar, ziyaretçiler ve üyeler oy verir, sonuçlar canlı görünür. Prototip; sade, hızlı, mobil öncelikli.

## 2. Teknoloji
- Python (yerelde 3.15, Vercel'de 3.12'ye sabitlenecek — bağımlılıklar her ikisinde de çalışmalı), Django 5.x/6.x (3.15 ile uyumlu en güncel sürüm), gunicorn gerekmez (Vercel zero-config).
- Veritabanı: yerelde SQLite, `DATABASE_URL` varsa Postgres (Supabase). `dj-database-url`, `psycopg[binary]`, `whitenoise`, `python-dotenv` (veya `django-environ`).
- Ön yüz: Django şablonları, saf CSS, saf JS (framework yok), Google Fonts: Fredoka (başlık) + Nunito (metin).
- Kod, değişken ve fonksiyon adları İngilizce; arayüz metinleri, URL'ler ve hata mesajları Türkçe.

## 3. Kapsam dışı (prototip)
E-posta doğrulama, parola sıfırlama, bitiş süresi, kategori, filtre, captcha, karanlık mod, OG görseli. (Bölüm 12.) Rate limit ve kayıt honeypot'u sonradan eklendi.

## 4. Klasör yapısı
```
manage.py
config/            settings.py, urls.py, wsgi.py
accounts/          models.py (User), forms.py, views.py, urls.py, admin.py, tests/
polls/             models.py, forms.py, views.py, services.py, urls.py, admin.py, voter.py, tests/
templates/         base.html, 404.html, 500.html, partials/ (_navbar, _messages), accounts/, polls/ (+ partials/_poll_card.html, _results.html)
static/css/main.css, static/js/main.js, static/img/ (logo.svg, favicon.svg)
scripts/supabase_enable_rls.sql
requirements.txt, .env.example, .gitignore, README.md, CLAUDE.md
```

## 5. Veri modelleri
### 5.1 accounts.User (AbstractUser tabanlı, İLK migration'dan önce)
- `email`: benzersiz, kayıtta küçük harfe çevrilir. `USERNAME_FIELD="email"`, `REQUIRED_FIELDS=["username"]`.
- `username`: 3–20 karakter, regex `^[A-Za-z0-9_]+$` (Türkçe harf yok), `iexact` benzersiz (`UniqueConstraint(Lower("username"))`).
- Özel manager: e-postayı normalize edip küçük harfe çevirir; `create_user`/`create_superuser` e-posta ile çalışır.
- E-posta hiçbir sayfada/JSON'da başka kullanıcıya gösterilmez.

### 5.2 polls.Poll
`author` (FK User, CASCADE, related_name="polls"), `question` (max 200), `description` (max 500, boş olabilir), `is_closed` (bool, False; yazar kapatınca), `closes_at` (datetime, null; süreli anket), `created_at` (auto_now_add). Sıralama: `-created_at`. `Poll.is_finished` = `is_closed` VEYA süresi dolmuş (`has_expired`); oy, sonuç görünürlüğü ve rozetler **her zaman `is_finished`** üzerinden karar verir, `is_closed` alanına doğrudan bakma. Oluşturma formundaki `duration` seçimi (Süresiz/1 sa/24 sa/3 gün/7 gün) `closes_at`'i ayarlar.

### 5.3 polls.Option
`poll` (FK, related_name="options", CASCADE), `text` (max 80), `order` (0–4). Sıralama: `order`. Poll başına 2–5 seçenek. Aynı ankette seçenek metni iexact tekrar edemez.

### 5.4 polls.Vote
`poll` (FK, related_name="votes"), `option` (FK, related_name="votes"), `user` (FK, null), `voter_token` (char 64, boş olabilir), `created_at`.
- `UniqueConstraint(fields=[poll, user], condition=user not null)`
- `UniqueConstraint(fields=[poll, voter_token], condition=voter_token != "")`
- Kayıtlı kullanıcı oyu `user` ile, ziyaretçi oyu `voter_token` ile saklanır.

## 6. Oylama kuralları
Ziyaretçi kimliği: imzalı çerez `kararsizim_voter` (rastgele uuid4 hex, `django.core.signing`, 1 yıl, HttpOnly, SameSite=Lax, üretimde Secure). Yoksa üretilir, yanıta yazılır.

`cast_vote(poll, option_id, user, voter_token)`:
1. Anket kapalıysa veya süresi dolmuşsa (`poll.is_finished`) → `PollClosed`.
2. `option_id`, bu ankete ait bir seçenek değilse → `InvalidOption`.
3. `has_voted` ise → `AlreadyVoted`.
4. `transaction.atomic()` içinde Vote oluştur (user varsa user, yoksa voter_token).
5. `IntegrityError` → `AlreadyVoted`.

Sonuç görünürlüğü: yalnızca oy vermiş, anketin yazarı olan veya anket kapalıysa herkes görür. Oy formu, anket açıkken ve kullanıcı oy vermemişken (yazar dahil) gösterilir.
`get_results`: seçenek başına oy sayısı, tam sayı yüzde (yuvarlama: 2/3→67, 1/3→33), `is_leading` (eşitlikte birden fazla), toplam oy; tek sorgu (annotate).
Bilinen sınır: çerez silinirse ziyaretçi tekrar oy verebilir.

## 7. URL'ler (ad → yol)
| ad | yol | not |
|---|---|---|
| poll_list | `/` | sayfa başı 10 |
| poll_create | `/anket/yeni/` | login_required |
| poll_detail | `/anket/<pk>/` | |
| poll_vote | `/anket/<pk>/oy/` | POST; Accept: json desteği |
| poll_close | `/anket/<pk>/kapat/` | POST, yazar, değilse 404 |
| poll_delete | `/anket/<pk>/sil/` | GET onay + POST, yazar, değilse 404 |
| my_polls | `/anketlerim/` | login_required |
| signup | `/kayit/` | |
| login | `/giris/` | |
| logout | `/cikis/` | sadece POST |

Tüm durum değiştiren işlemler POST + CSRF. GET hiçbir şeyi değiştirmez.

## 8. Arayüz ve JS
**Renkler (`:root`):** `--bg:#FFF8EC` (krem), `--ink:#2B2540`, `--primary:#7C4DFF` (mor), `--primary-dark:#5B34D6`, seçenek renkleri `--opt-1:#7C4DFF` mor, `--opt-2:#FF8A3D` turuncu, `--opt-3:#19C2B0` turkuaz, `--opt-4:#FF5C9A` pembe, `--opt-5:#FFD23F` sarı; turuncu/turkuaz/pembe/sarı zeminde koyu metin. Ölçüler: `--radius:16px`, `--radius-lg:24px`, gölgeler yumuşak. İçerik en fazla ~720px, kırılma noktaları 640px / 960px, mobil öncelikli.
**Stil:** genç/enerjik; kalın "3D" butonlar (basınca iner), yuvarlak köşeler, hafif sabit blob arka plan, kartlarda tint zemin, sıraya göre renkli sol şerit. `prefers-reduced-motion`'da animasyon kapalı. Odak halkası (`:focus-visible`) net.
**Seçenek sınıfları:** `.option--1 … .option--5` (order'a göre).
**Formlar:** büyük yuvarlak alanlar, label, alan altında hata.
**JSON oy yanıtı** (`Accept: application/json`):
```json
{"ok": true, "message": "Oyun kaydedildi! 🙌", "total_votes": 3,
 "results": [{"option_id": 1, "text": "...", "votes": 2, "percent": 67, "is_leading": true, "is_mine": true, "order": 0}]}
```
Hata: `{"ok": false, "message": "..."}` ile 400 (geçersiz seçenek), 403 (kapalı), 409 (zaten oy verdi). E-posta asla yer almaz.
**JS (tek dosya, saf, progressive enhancement; JS kapalıyken her şey çalışır). 6 görev:** (1) anket formunda dinamik seçenek ekle/çıkar (2–5), (2) fetch ile oylama + sonuç çizimi (CSRF çerezden, hata olursa normal gönderime düş, buton kilidi), (3) sonuç çubuğu animasyonu, (4) toast 4 sn sonra kaybolur + kapat butonu, (5) "Linki kopyala", (6) mobil menü (aria-expanded). Metinler `textContent` ile basılır, `innerHTML` yok.

## 9. Ayarlar (settings.py)
- Ortam değişkenleri: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DATABASE_URL`, `ALLOWED_HOSTS`. `.env` / `.env.local` yüklenir.
- `DATABASE_URL` yoksa SQLite; varsa Postgres: `CONN_MAX_AGE=0`, `DISABLE_SERVER_SIDE_CURSORS=True`, `sslmode=require`.
- `LANGUAGE_CODE="tr"`, `TIME_ZONE="Europe/Istanbul"`, `AUTH_USER_MODEL="accounts.User"`.
- Static: `STATIC_URL`, `STATIC_ROOT="staticfiles"`, WhiteNoise.
- DEBUG=False: `ALLOWED_HOSTS` + `.vercel.app`, `CSRF_TRUSTED_ORIGINS=["https://*.vercel.app"]`, secure cookie'ler, `SECURE_PROXY_SSL_HEADER`, HSTS, SSL redirect uygun şekilde.
- Gizli bilgiler asla commit'lenmez.

## 10. Deploy
Vercel Django zero-config (manage.py kökte, WSGI_APPLICATION doğru, STATIC_ROOT tanımlı), Python 3.12 sabitlenir. Supabase Postgres: migration Session pooler (5432) ile yerelden, uygulama Transaction pooler (6543) ile. Supabase Data API public tabloları açmamalı: Data API kapalı veya tüm tablolarda politikasız RLS (`scripts/supabase_enable_rls.sql`).

## 11. Test ve kalite
Django `TestCase`; her aşamada `makemigrations`, `migrate`, `check`, `test` temiz. Liste/detay/anketlerim için `assertNumQueries` (N+1 yok). Gizlilik testi: e-posta yanıtlarda yok.

## 12. Sonraki adımlar (prototip sonrası)
Liste filtreleri (yeni/popüler/kapanmak üzere), captcha, e-posta doğrulama + parola sıfırlama, kategoriler, Open Graph önizleme, karanlık mod.

## 13. Aşama durumu
- [x] Aşama 1 — İskelet, ayarlar, User, temel şablon
- [x] Aşama 2 — Kayıt, giriş, çıkış
- [x] Aşama 3 — Anket oluşturma, liste, detay
- [x] Aşama 4 — Oylama, sonuçlar, anketlerim, kapat/sil
- [x] Aşama 5 — Arayüz cilası ve JS
- [x] Aşama 6 (kod/dokümantasyon tarafı; Supabase + Vercel hesap adımları kullanıcıda) — Supabase + Vercel deploy
- [x] Aşama 7 — Son kontrol ve temizlik

## 14. Güncel durum ve devam notları (yeni oturum buradan başlasın)

_Son güncelleme: 2026-11-13. Son commit'ler `main` dalında GitHub'a gönderildi._

**Bitenler:** Aşama 1–7 (bölüm 13) + sonradan eklenenler: spam koruması (rate limit + kayıt honeypot'u, `config/ratelimit.py`), yazarın kendi anketine oy verebilmesi, anket bitiş süresi + canlı geri sayım (`Poll.closes_at`, `is_finished`), `scripts/run_prodlike.py`. 125 test geçiyor (`python manage.py test`).

**Altyapı (hazır, gizli değerler dosyada):**
- Supabase projesi `kararsizim`, ref `xwzxrbnwmrjbidathhlo`, bölge Frankfurt (eu-central-1). Havuz adresi `aws-1-eu-central-1.pooler.supabase.com` (`aws-0` bu projede çalışmaz). Kullanıcı `postgres.<ref>`. Session pooler 5432 (migration/yerel), Transaction pooler 6543 (Vercel).
- Tablolar kurulu (migration 0001 + `polls.0002_poll_closes_at` uygulandı), `django_cache` tablosu elle oluşturuldu (rate limit için), **tüm public tablolarda RLS açık**, Security Advisor temiz (yalnızca "RLS açık, politika yok" INFO notları — bilinçli). Yeni migration yeni tablo getirirse `scripts/supabase_enable_rls.sql` tekrar çalıştırılmalı.
- Veritabanları şu an **boş**: Supabase'de 0 kullanıcı/anket/oy; yerel `db.sqlite3` de boş. Yönetici hesabı (`createsuperuser`) açılmadı.
- Gizli değerler **yalnızca git'e girmeyen `.env.local`** içinde: aktif `DATABASE_URL` (5432) ve yorum satırı olarak Vercel için hazırlanmış `DATABASE_URL` (6543) + `DJANGO_SECRET_KEY`. Parola sohbette göründü ve zayıf → **canlıdan önce Supabase panelinde değiştirilmeli**; değişince `.env.local`'deki iki adres ve Vercel'deki değer güncellenmeli (parolada `ı` gibi karakterler URL'de yüzde-kodlanmalı).
- `python scripts/run_prodlike.py` siteyi DEBUG=False + 6543 ile `http://localhost:8000`'de çalıştırır; denendi: sayfalar, statik dosyalar, 404, güvenlik başlıkları, CSRF çerezi sorunsuz. (`localhost` kullan, `127.0.0.1` değil; Safari'de Secure çerez sorunu olabilir.)

**Sıradaki iş: Vercel deploy (HİÇ YAPILMADI).**
- Vercel MCP bağlantısı ekip `team_ufK1mqjQHGZZVVmNeEG3AA8U` (`yusufkaragozoglu1-9763`) için iki onaya rağmen 403 verdi; projeyi otomatik oluşturamadık. Önce `list_projects` ile tekrar denenebilir; olmazsa kullanıcıyla panelden ilerle.
- Adımlar: https://vercel.com/new → `yusufkaragozoglu1-debug/karas-z-m` içe aktar (Django otomatik algılanır, `vercel.json` yok, Python 3.12 `.python-version` ile) → Environment Variables (Production): `DJANGO_SECRET_KEY` ve `DATABASE_URL` (6543) değerlerini `.env.local`'deki yorum satırlarından al; `DJANGO_DEBUG` ekleme veya `False` → Deploy.
- Deploy sonrası kontrol: sayfa açılıyor mu, **CSS/JS canlıda yükleniyor mu** (statik dosya ayarı `WHITENOISE_USE_FINDERS` ile canlıda henüz doğrulanmadı), kayıt/giriş/anket/oy (gizli pencereden de), süreli anket, rate limit 429, Vercel loglarında hata. `ALLOWED_HOSTS` `.vercel.app`'i otomatik içerir; özel alan adı için `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS` env'i gerekir.
- Canlı için yönetici hesabı: yerelden (`.env.local` 5432 ile) `python manage.py createsuperuser`.

**Sonra (öncelik sırası, README "Sonraki adımlar"):** liste filtreleri (en yeni/en popüler/kapanmak üzere), süreyi sonradan uzatma, captcha (Turnstile anahtarı gerekir), e-posta doğrulama + parola sıfırlama (e-posta servisi gerekir), kategoriler/OG görseli/karanlık mod.

**Kullanıcı tercihleri:** Türkçe konuş. Soru sormadan, makul varsayımla ilerle ve varsayımı belirt. "faz N" demesi belirsiz: şimdiye dek sıradaki işi kastetti. Commit/push'u açıkça isteyince yap (commit'ten önce staged diff'te parola/anahtar taraması yap). Canlı hesaplarda (Supabase/Vercel) kalıcı değişiklik yapmadan önce onay al.
