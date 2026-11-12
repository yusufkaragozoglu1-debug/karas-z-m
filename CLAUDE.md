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

Lint/format aracı yapılandırılmamış. `DJANGO_DEBUG` varsayılanı `False` (ve `DJANGO_SECRET_KEY` zorunlu); yerel `.env` (git'e girmez) `DJANGO_DEBUG=True` içerir. Testler sırasında "staticfiles dizini yok" uyarısı zararsızdır.

## Mimari (birden çok dosyayı okumayı gerektiren noktalar)

- **Oy mantığı `polls/services.py` içinde**, view'larda değil. `cast_vote` sırayla kapalı → geçersiz seçenek → zaten oy verilmiş kontrolü yapar, `VoteError` alt sınıfları (`PollClosed` 403, `InvalidOption` 400, `AlreadyVoted` 409) hem mesajı hem HTTP kodunu taşır; `polls/views.py:poll_vote` bunları ya `messages`+redirect ya da JSON'a (`Accept: application/json`) çevirir. Race durumu `Vote` üzerindeki koşullu `UniqueConstraint`'ler + `IntegrityError` → `AlreadyVoted` ile çözülür.
- **Oy kimliği**: üye oyu `user` ile, ziyaretçi oyu imzalı `kararsizim_voter` çerezindeki token ile (`polls/voter.py`) saklanır; ikisi aynı satırda tutulmaz. `has_voted`/`get_user_vote`/`voted_poll_ids` ikisini birden (`user` VEYA token) kontrol eder — ziyaretçi oy verip sonra giriş yaparsa tekrar oy veremez.
- **Sonuç görünürlüğü** `poll_detail` içinde karar verilir: yazar, kapalı anket veya oy vermiş olan sonucu görür; diğerleri oy formunu görür (yazarın UI'dan oy vermesi bilinçli olarak yok). `get_results` tek sorguda `annotate` ile sayı/yüzde/`is_leading` üretir; aynı dict yapısı hem `_results.html` şablonuna hem JSON yanıtına gider (şema bölüm 8).
- **N+1 yasağı**: liste/anketlerim `Poll` sorgusunu `_annotated_polls()` ile paylaşır; sayfadaki "oy verdin" bilgisi tek sorguyla gelir. `assertNumQueries` benzeri testler (anket sayısı artınca sorgu sayısı sabit) var — yeni sorgu eklerken bozma.
- **Kullanıcı**: `accounts.User` e-posta ile girer (`USERNAME_FIELD="email"`), e-posta `save()` ve manager'da küçük harfe çevrilir, kullanıcı adı `Lower("username")` kısıtıyla iexact benzersizdir. E-posta hiçbir şablonda/JSON'da gösterilmez (testle korunuyor).
- **Ayarlar** (`config/settings.py`): `.env` sonra `.env.local` yüklenir; `DATABASE_URL` yoksa SQLite, varsa Postgres (`CONN_MAX_AGE=0`, server-side cursor kapalı, `sslmode=require`). Üretim güvenlik ayarları `DEBUG=False` iken devreye girer; `VOTER_COOKIE_SECURE = not DEBUG`.
- **Frontend**: tek `static/css/main.css` ve `static/js/main.js`, framework yok. JS yalnızca ilerleyen geliştirme (Aşama 5); JS kapalıyken her akış çalışmalı. Metinler `textContent` ile basılır.
- Python yerelde 3.15, Vercel'de 3.12 hedefleniyor; her iki sürümde çalışan bağımlılıklar seç.
- Git deposunun kökü proje değil `C:\Users\ASUS` (ana dizin): commit atarken yalnızca `Kararsizim` klasörünü stage'le (`git add .` bu klasörde).

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
E-posta doğrulama, parola sıfırlama, bitiş süresi, kategori, filtre, rate limit, captcha, karanlık mod, OG görseli. (Bölüm 12.)

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
`author` (FK User, CASCADE, related_name="polls"), `question` (max 200), `description` (max 500, boş olabilir), `is_closed` (bool, False), `created_at` (auto_now_add). Sıralama: `-created_at`.

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
1. Anket kapalıysa → `PollClosed`.
2. `option_id`, bu ankete ait bir seçenek değilse → `InvalidOption`.
3. `has_voted` ise → `AlreadyVoted`.
4. `transaction.atomic()` içinde Vote oluştur (user varsa user, yoksa voter_token).
5. `IntegrityError` → `AlreadyVoted`.

Sonuç görünürlüğü: yalnızca oy vermiş, anketin yazarı olan veya anket kapalıysa herkes görür. Aksi halde oy formu gösterilir.
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
Bitiş süresi + geri sayım, liste filtreleri (yeni/popüler/kapanmak üzere), rate limit + captcha, e-posta doğrulama + parola sıfırlama, kategoriler, Open Graph önizleme, karanlık mod.

## 13. Aşama durumu
- [x] Aşama 1 — İskelet, ayarlar, User, temel şablon
- [x] Aşama 2 — Kayıt, giriş, çıkış
- [x] Aşama 3 — Anket oluşturma, liste, detay
- [x] Aşama 4 — Oylama, sonuçlar, anketlerim, kapat/sil
- [ ] Aşama 5 — Arayüz cilası ve JS
- [ ] Aşama 6 — Supabase + Vercel deploy
- [ ] Aşama 7 — Son kontrol ve temizlik
