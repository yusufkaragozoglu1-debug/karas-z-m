# Kararsızım — Claude Code Aşama Promptları

Bu dosya, projeyi Claude Code ile **adım adım** geliştirmek için hazır promptları içerir.
Projenin tüm detayları `CLAUDE.md` dosyasındadır; promptlar o dosyaya dayanır.

## Nasıl kullanılır?

1. Boş bir klasör aç (`kararsizim/`), içine `CLAUDE.md` ve `ADIMLAR.md` dosyalarını koy.
2. Klasörde `git init` yap ve Claude Code'u başlat.
3. Her aşamada:
   - Önce **plan modunu** aç (Shift+Tab ile) ve promptu yapıştır. Claude planı gösterir; uygunsa onayla.
   - Aşama bitince Claude'un verdiği komutlarla uygulamayı çalıştır ve **"Kontrol listesi"**ni kendin dene.
   - Her şey yolundaysa commit at: `git add . && git commit -m "Aşama X"`
   - Yeni aşamaya geçmeden `/clear` ile sohbeti temizle. `CLAUDE.md` her oturumda yeniden okunduğu için bilgi kaybolmaz.
4. Bir şey bozulursa sonraki aşamaya geçme; aynı oturumda hatayı anlatıp düzelttir.

> İpucu: Bir aşama çok büyük gelirse "Bu aşamanın sadece ilk yarısını yap" diyebilirsin.

---

## Aşama 0 — Senin yapman gerekenler (Claude Code'a gerek yok)

- [ ] Bilgisayarda Python 3.12 ve Git kurulu olsun.
- [ ] GitHub'da boş bir repo aç (`kararsizim`).
- [ ] Supabase hesabı aç (veritabanı Aşama 6'da lazım olacak, şimdilik SQLite ile çalışacağız).
- [ ] Vercel hesabı aç ve GitHub ile bağla (Aşama 6'da lazım).

---

## Aşama 1 — Proje iskeleti, ayarlar, kullanıcı modeli, temel şablon

```
CLAUDE.md dosyasını baştan sona oku. Şimdi sadece AŞAMA 1'i uygula, sonraki aşamalara geçme.

Yapılacaklar:
1. Python sanal ortamı (.venv) oluşturma ve kurulum komutlarını README.md'ye yaz.
2. requirements.txt'yi CLAUDE.md'deki bağımlılıklarla oluştur.
3. "config" adında Django projesi ve "accounts", "polls" adında iki uygulama oluştur. Klasör yapısı CLAUDE.md bölüm 4'teki gibi olsun.
4. config/settings.py'yi CLAUDE.md bölüm 9'daki kurallara göre yaz (ortam değişkenleri, SQLite yedeği, DATABASE_URL varsa Postgres + CONN_MAX_AGE=0 + DISABLE_SERVER_SIDE_CURSORS + sslmode, tr dil, İstanbul saat dilimi, static ayarları, güvenlik ayarları).
5. .env.example ve .gitignore oluştur (.venv, .env, .env.local, db.sqlite3, staticfiles, __pycache__).
6. accounts.User özel kullanıcı modelini CLAUDE.md bölüm 5.1'e göre İLK MIGRATION'DAN ÖNCE oluştur (USERNAME_FIELD="email", REQUIRED_FIELDS=["username"], kullanıcı adı regex ve iexact benzersizlik, e-postayı küçük harfe çeviren manager). Admin'e kaydet.
7. templates/base.html: <html lang="tr">, meta viewport, Google Fonts (Fredoka + Nunito), static/css/main.css ve defer ile static/js/main.js, navbar partial'ı, Django messages partial'ı, {% block content %}.
8. static/css/main.css: CLAUDE.md bölüm 8'deki :root renk/ölçü değişkenleri, temel reset, tipografi, .container, .btn ve .btn--primary / --ghost / --danger, .card temel stilleri. Şimdilik sade ama palet doğru olsun.
9. static/js/main.js: boş iskelet + DOMContentLoaded.
10. polls uygulamasında geçici bir anasayfa view'u ("Kararsız mı kaldın? Topluluğa sor!" karşılama alanı) ve URL'leri bağla.
11. 404.html ve 500.html şablonlarını base.html'den türeterek sade şekilde oluştur.
12. Kullanıcı modeli için testler: e-posta küçük harfe çevriliyor mu, kullanıcı adı büyük/küçük harf duyarsız benzersiz mi, geçersiz kullanıcı adı reddediliyor mu.

Bitince:
- makemigrations, migrate, check ve test komutlarını çalıştır, hepsi temiz olsun.
- Bana uygulamayı yerelde çalıştırmak için gereken komutları adım adım yaz.
- CLAUDE.md bölüm 13'te Aşama 1'i işaretle.
```

**Kontrol listesi**
- [ ] `python manage.py runserver` sonrası `http://127.0.0.1:8000` açılıyor, krem arka plan ve mor buton görünüyor.
- [ ] Türkçe karakterler (ğ, ş, ı, İ) doğru görünüyor.
- [ ] `python manage.py createsuperuser` e-posta + kullanıcı adı soruyor; `/admin/` girişi çalışıyor.
- [ ] `python manage.py test` geçiyor.

---

## Aşama 2 — Kayıt, giriş, çıkış

```
CLAUDE.md'yi oku. Aşama 1 tamamlandı. Şimdi sadece AŞAMA 2'yi uygula.

Yapılacaklar:
1. accounts/forms.py:
   - SignupForm: kullanıcı adı, e-posta, parola, parola tekrar. Kullanıcı adı ve e-posta için büyük/küçük harf duyarsız benzersizlik kontrolü, Türkçe ve anlaşılır hata mesajları ("Bu kullanıcı adı alınmış", "Bu e-posta ile zaten bir hesap var" gibi). Django'nun parola doğrulayıcıları çalışsın.
   - LoginForm: e-posta + parola (Django AuthenticationForm'u e-posta ile çalışacak şekilde uyarlayabilirsin). Hatalı girişte genel bir mesaj ver: "E-posta veya parola hatalı."
2. accounts/views.py ve urls.py: /kayit/, /giris/, /cikis/ (çıkış sadece POST). CLAUDE.md bölüm 7'deki URL adlarını kullan.
   - Kayıt başarılı → otomatik giriş → anasayfa → "Hoş geldin @kullaniciadi! 🎉" mesajı.
   - Giriş yapmış kullanıcı /kayit/ veya /giris/'e girerse anasayfaya yönlendir.
   - ?next= parametresi güvenli şekilde desteklensin.
3. templates/accounts/signup.html ve login.html: CLAUDE.md bölüm 8'deki form tasarımına uygun, büyük yuvarlak alanlar, label'lar, alan altında hata mesajları, alt kısımda "Hesabın yok mu? Kayıt ol" / "Zaten üye misin? Giriş yap" bağlantıları.
4. Navbar'ı güncelle: ziyaretçide "Giriş" ve "Kayıt ol"; üyede "@kullaniciadi" ve "Çıkış" (POST formu içinde buton). Navbar'da e-posta ASLA gösterilmesin.
5. Testler: başarılı kayıt, tekrar eden kullanıcı adı/e-posta (farklı harf büyüklüğüyle), parolalar eşleşmiyor, başarılı giriş, hatalı giriş, çıkışın GET ile çalışmaması, next yönlendirmesi.

Bitince test ve check komutlarını çalıştır, bana deneme adımlarını yaz, CLAUDE.md'de Aşama 2'yi işaretle.
```

**Kontrol listesi**
- [ ] Kayıt olunca otomatik giriş yapılıyor ve navbar'da `@kullaniciadi` görünüyor.
- [ ] `Ali` ile kayıt olduktan sonra `ali` ile tekrar kayıt olunamıyor.
- [ ] Yanlış parolayla giriş anlaşılır bir hata veriyor.
- [ ] Çıkış çalışıyor.

---

## Aşama 3 — Anket oluşturma, liste, detay

```
CLAUDE.md'yi oku. Aşama 1–2 tamamlandı. Şimdi sadece AŞAMA 3'ü uygula. Oylama bu aşamada YOK, sadece Poll ve Option.

Yapılacaklar:
1. polls/models.py: Poll ve Option modellerini CLAUDE.md bölüm 5.2 ve 5.3'e göre yaz. (Vote modelini de şimdi ekle ama henüz kullanma — bölüm 5.4'teki UniqueConstraint'lerle birlikte. Böylece Aşama 4'te migration karmaşası olmaz.) Admin'e Poll'u Option inline ile, Vote'u ayrı kaydet.
2. polls/forms.py: PollCreateForm — question, description, option_1 … option_5. İlk iki seçenek zorunlu; toplamda 2–5 dolu seçenek; boşlukları kırp; tekrarlı seçenekleri (büyük/küçük harf duyarsız) reddet; uzunluk sınırları. Türkçe hata mesajları.
3. polls/views.py:
   - poll_list ("/"): tüm anketler, en yeni üstte, sayfa başına 10, select_related("author") ve annotate(total_votes=Count("votes"), option_count=Count("options", distinct=True)). N+1 sorgu olmasın.
   - poll_detail ("/anket/<pk>/"): soru, açıklama, @yazar, tarih (timesince), seçenekler sırayla. Bu aşamada seçenekler sadece listelensin.
   - poll_create ("/anket/yeni/"): login_required; kaydı transaction.atomic() içinde yap; başarılıysa detay sayfasına yönlendir ve "Anketin yayında! 🎉" mesajı göster.
4. Şablonlar: polls/list.html (karşılama alanı + kartlar + sayfalama + boş durum), partials/_poll_card.html, polls/detail.html, polls/create.html. Seçenekler order değerine göre .option--1 … .option--5 renk sınıflarını alsın. Ziyaretçi "Anket oluştur" butonuna basınca giriş sayfasına (next ile) gitsin.
5. Navbar'a üyeler için "Anket oluştur" bağlantısı ekle.
6. Testler: ziyaretçi /anket/yeni/'ye girince girişe yönleniyor; 1 seçenekle anket oluşturulamıyor; 6. seçenek kabul edilmiyor (form zaten 5 alan); tekrarlı seçenek reddediliyor; başarılı oluşturma; liste sayfası anketleri yeniden eskiye sıralıyor; detay sayfasında yazarın kullanıcı adı VAR ama e-postası YOK (gizlilik testi); liste sayfasının sorgu sayısı anket sayısıyla artmıyor (assertNumQueries).

Bitince test ve check komutlarını çalıştır, bana deneme adımlarını yaz, CLAUDE.md'de Aşama 3'ü işaretle.
```

**Kontrol listesi**
- [ ] Üye olarak 2, 3 ve 5 seçenekli anketler oluşturabiliyorum.
- [ ] Çıkış yapınca anketleri hâlâ görebiliyorum ama "Anket oluştur" beni girişe götürüyor.
- [ ] Anket kartında `@kullaniciadi` görünüyor, e-posta hiçbir yerde yok.
- [ ] Seçeneklerin her biri farklı renkte.

---

## Aşama 4 — Oylama, sonuçlar, anketlerim, kapatma/silme

```
CLAUDE.md'yi oku. Aşama 1–3 tamamlandı. Şimdi sadece AŞAMA 4'ü uygula. Bu aşamada JavaScript YOK; her şey normal form gönderimiyle çalışsın (JS Aşama 5'te).

Yapılacaklar:
1. Ziyaretçi kimliği: CLAUDE.md bölüm 6'daki "kararsizim_voter" imzalı çerezini yöneten küçük yardımcı fonksiyonlar yaz (oku / yoksa üret / yanıta yaz). Üretimde secure=True.
2. polls/services.py:
   - has_voted(poll, user, voter_token) ve get_user_vote(...)
   - cast_vote(poll, option_id, user, voter_token): bölüm 6'daki 5 adımı uygula, IntegrityError'ı "zaten oy verdin" olarak ele al. Hata durumları için anlamlı bir exception sınıfı kullan.
   - get_results(poll): her seçenek için oy sayısı, tam sayı yüzde, is_leading (eşitlikte birden fazla önde olabilir), toplam oy. Tek sorgu ile (annotate).
3. poll_vote view'u ("/anket/<pk>/oy/", sadece POST): servisi çağır, başarıda "Oyun kaydedildi! 🙌" mesajıyla detaya yönlendir, hatada uygun mesajla detaya yönlendir. Ayrıca istek "Accept: application/json" içeriyorsa CLAUDE.md bölüm 8'deki JSON formatında yanıt ver (Aşama 5'te JS kullanacak) ve uygun HTTP kodlarını döndür.
4. poll_detail'i güncelle:
   - Oy vermediyse ve anket açıksa: radio tabanlı oy formu + "Oyumu ver" butonu.
   - Oy verdiyse / yazar ise / anket kapalıysa: partials/_results.html (renkli çubuklar, yüzde, oy sayısı, "Senin seçimin ✓", "👑 Önde", oy yoksa "Henüz oy yok").
   - Yazar ise "Anketi kapat" (POST) ve "Sil" butonları.
5. poll_close ("/anket/<pk>/kapat/", POST, sadece yazar) ve poll_delete ("/anket/<pk>/sil/", GET onay sayfası + POST silme, sadece yazar). Yazar değilse 404.
6. my_polls ("/anketlerim/", login_required): kullanıcının anketleri, toplam oy, açık/kapalı durumu. Navbar'a "Anketlerim" ekle.
7. Liste sayfasındaki kartlara "Oy verdin ✓" ve "Kapalı 🔒" rozetlerini ekle. Kullanıcının oy verdiği anket ID'lerini sayfa başına TEK sorguyla al.
8. Testler: ziyaretçi oy verebiliyor; aynı çerezle ikinci oy reddediliyor; üye ikinci kez oy veremiyor; başka bir ankete ait option_id reddediliyor; kapalı ankete oy verilemiyor; GET ile oy verilemiyor; oy vermeden sonuçlar görünmüyor; oy verdikten sonra görünüyor; yazar sonuçları her zaman görüyor; yazar olmayan kapatma/silme yapamıyor (404); JSON yanıtı doğru formatta ve e-posta içermiyor; yüzdeler doğru hesaplanıyor (ör. 2/3 → 67, 1/3 → 33).

Bitince test ve check komutlarını çalıştır, bana deneme adımlarını yaz (özellikle gizli pencereyle ziyaretçi olarak oy verme), CLAUDE.md'de Aşama 4'ü işaretle.
```

**Kontrol listesi**
- [ ] Gizli pencerede (üye olmadan) oy verebiliyorum, sonra tekrar oy veremiyorum.
- [ ] Oy vermeden sonuçları göremiyorum; oy verince renkli çubuklar çıkıyor.
- [ ] Kendi anketimi kapatınca oylama duruyor, sonuçlar herkese açılıyor.
- [ ] Başkasının anketini silmeye çalışınca 404 alıyorum.

---

## Aşama 5 — Arayüz cilası ve JavaScript

```
CLAUDE.md'yi oku. Aşama 1–4 tamamlandı ve uygulama JS olmadan tam çalışıyor. Şimdi sadece AŞAMA 5'i uygula: görsel cila + aşamalı geliştirme (progressive enhancement) JavaScript'i. Python tarafındaki iş mantığını DEĞİŞTİRME (gerekirse sadece küçük şablon düzenlemeleri).

Tasarım (CLAUDE.md bölüm 8'i birebir uygula):
1. Genç ve enerjik bir his: krem arka plan, arka planda çok hafif sabit renkli bloblar (radial-gradient), kartlarda tint zeminler, kalın "3D" butonlar (basınca aşağı iner), yuvarlak köşeler, yumuşak gölgeler.
2. Anket kartları: sıraya göre değişen renkli sol şerit, hover'da yukarı kalkma, rozetler.
3. Oy seçenekleri: tam genişlik renkli kartlar; radio görsel olarak gizli ama klavyeyle erişilebilir; seçilince dolu renk + ✓; :focus-visible net görünsün.
4. Sonuç çubukları: seçenek renginde, 0'dan hedefe animasyonla dolma.
5. Toast mesajları, boş durumlar (büyük emoji + esprili metin + buton), form odak halkaları.
6. Mobil öncelikli düzen (640px / 960px kırılma noktaları, içerik en fazla ~720px), mobilde hamburger menü.
7. Kontrast kurallarına uy (turuncu/turkuaz/pembe zeminde koyu metin). prefers-reduced-motion'da animasyonları kapat.
8. Basit bir SVG logo ve favicon ekle (soru işareti / iki ok gibi "kararsızlık" temalı, kendi tasarımın).

JavaScript (static/js/main.js, tek dosya, saf JS, bölüm 8'deki 6 görev):
1. Anket oluşturma: 3–5. seçenekleri gizle, "+ Seçenek ekle" ile aç, 5'e ulaşınca butonu gizle, "✕" ile kaldır (en az 2 kalsın).
2. Oylama: formu fetch ile POST et (X-CSRFToken çerezden, Accept: application/json), dönen JSON ile _results.html ile aynı görünümde sonuçları çiz, çubukları animasyonla doldur. Ağ hatası veya beklenmeyen yanıtta normal form gönderimine düş. Gönderim sırasında butonu devre dışı bırak (çift tıklama engeli).
3. Sonuç çubuğu animasyonu (sayfa yüklenince de çalışsın).
4. Toast'ların 4 saniye sonra kaybolması (kapat butonu da olsun).
5. "Linki kopyala" butonu (Clipboard API, başarıda "Kopyalandı! ✓").
6. Mobil menü aç/kapa (aria-expanded güncellensin).
JS'den gelen metinleri innerHTML ile değil textContent ile bas (XSS'e karşı).

Bitince: JS kapalıyken de her şeyin çalıştığını kontrol et, mevcut testlerin hâlâ geçtiğini doğrula, bana masaüstü ve mobil (tarayıcı geliştirici araçlarında) deneme adımlarını yaz, CLAUDE.md'de Aşama 5'i işaretle.
```

**Kontrol listesi**
- [ ] Oy verince sayfa yenilenmeden sonuçlar animasyonla çıkıyor.
- [ ] Tarayıcıda JavaScript'i kapatınca da oy verebiliyor ve anket oluşturabiliyorum.
- [ ] Telefon boyutunda (DevTools) her şey düzgün, menü açılıp kapanıyor.
- [ ] Sadece klavyeyle (Tab / Space / Enter) oy verebiliyorum.

---

## Aşama 6 — Supabase + Vercel deploy

**Önce senin yapacakların:**
1. Supabase'de yeni proje oluştur, veritabanı parolasını not al.
2. Supabase panelinde **Connect** bölümünden iki adresi kopyala:
   - Transaction pooler (port **6543**) → Vercel'de kullanılacak
   - Session pooler (port **5432**) → yerelden migration için
3. Projeyi GitHub'a gönder (`git push`).

```
CLAUDE.md'yi oku. Aşama 1–5 tamamlandı. Şimdi sadece AŞAMA 6'yı uygula: Supabase (Postgres) ve Vercel'e deploy hazırlığı. CLAUDE.md bölüm 9 ve 10'u esas al.

Yapılacaklar:
1. Vercel'in güncel Django dokümanını kontrol et (https://vercel.com/docs/frameworks/full-stack/django) ve projenin zero-config algılamaya uygun olduğunu doğrula: manage.py kökte, WSGI_APPLICATION doğru, STATIC_ROOT tanımlı. Python 3.12 sürümünün Vercel'de nasıl sabitlendiğini dokümandan bul ve uygula. Gerekmedikçe vercel.json ekleme.
2. settings.py'nin üretim ayarlarını gözden geçir: DEBUG=False iken ALLOWED_HOSTS (.vercel.app), CSRF_TRUSTED_ORIGINS (https://*.vercel.app), secure cookie'ler, SECURE_PROXY_SSL_HEADER, voter çerezinin secure olması. DATABASE_URL ile Postgres bağlantısında CONN_MAX_AGE=0, DISABLE_SERVER_SIDE_CURSORS=True, sslmode=require.
3. Yerelde .env.local içine Session pooler adresini DATABASE_URL olarak koyup "python manage.py migrate" ve "createsuperuser" çalıştırmam için adım adım komutları README.md'ye yaz. Migration'ların transaction pooler üzerinden ÇALIŞTIRILMAYACAĞINI belirt.
4. Supabase güvenliği: Django tabloları public şemada olduğu için Data API'nin bu tabloları dışarı açmaması gerekiyor. Bana iki seçeneği açıkla (Data API'yi kapatmak veya tüm tablolarda politikasız RLS açmak) ve RLS seçeneği için Supabase SQL Editor'da çalıştırabileceğim, public şemadaki tüm tablolarda RLS'yi etkinleştiren bir SQL betiği hazırla (scripts/supabase_enable_rls.sql). Yeni migration'larla gelen tablolar için tekrar çalıştırılması gerektiğini README'ye not et.
5. README.md'ye "Vercel'e deploy" bölümü ekle: GitHub reposunu Vercel'e import etme, girilmesi gereken ortam değişkenleri (DJANGO_SECRET_KEY nasıl üretilir dahil), DATABASE_URL için transaction pooler adresinin kullanılması, deploy sonrası kontrol.
6. "python manage.py check --deploy" çalıştır, çıkan uyarıları prototip için mantıklı olanları düzelterek gider, kalanları README'de gerekçesiyle not et.

Gizli bilgileri (parola, secret key, bağlantı adresi) ASLA dosyalara yazma veya commit'leme; sadece .env.example'da boş/örnek değer olsun.

Bitince bana deploy için yapmam gereken adımları sırayla, numaralı liste halinde yaz ve CLAUDE.md'de Aşama 6'yı işaretle.
```

**Kontrol listesi**
- [ ] Supabase **Table Editor**'da `accounts_user`, `polls_poll`, `polls_option`, `polls_vote` tabloları var.
- [ ] Supabase **Security Advisor** RLS uyarısı vermiyor (veya Data API kapalı).
- [ ] `https://<proje>.vercel.app` açılıyor, CSS/JS yükleniyor.
- [ ] Canlıda kayıt, giriş, anket oluşturma ve gizli pencereden oy verme çalışıyor.
- [ ] Vercel loglarında hata yok.

---

## Aşama 7 — Son kontrol ve temizlik

```
CLAUDE.md'yi oku. Tüm aşamalar tamamlandı ve uygulama canlıda. Şimdi AŞAMA 7: genel gözden geçirme. Yeni özellik EKLEME.

1. Tüm kodu CLAUDE.md'deki şartnameye göre gözden geçir; şartnameden sapan her yeri listele ve düzelt.
2. Güvenlik kontrolü: tüm POST'larda CSRF var mı, GET hiçbir şeyi değiştirmiyor mu, yazar kontrolleri her yerde mi, e-posta hiçbir şablonda / JSON'da başka kullanıcıya gösteriliyor mu, |safe veya innerHTML kullanımı var mı, gizli bilgi commit'lenmiş mi.
3. Performans: liste, detay ve anketlerim sayfalarında N+1 sorgu var mı? Gerekirse assertNumQueries testleri ekle.
4. Erişilebilirlik: label'lar, aria-label'lar, kontrast, klavye ile gezinme, odak görünürlüğü.
5. Kullanılmayan kod, dosya ve CSS'i temizle.
6. README.md'yi son haline getir: proje tanımı, ekran özeti, yerel kurulum, test çalıştırma, deploy, bilinen sınırlamalar (çerez silinince tekrar oy verilebilmesi vb.) ve CLAUDE.md bölüm 12'deki "sonraki adımlar" listesi.
7. Tüm testleri çalıştır.

Sonunda bana yaptığın değişikliklerin kısa bir özetini ve prototipten sonraki geliştirmeler için öncelik sırasıyla 5 öneri ver. CLAUDE.md'de Aşama 7'yi işaretle.
```

---

## Sonrası için fikir havuzu (prototipten sonra)

Bunlar bilerek prototipe alınmadı. İleride her biri ayrı bir aşama olarak eklenebilir:

- Anket bitiş süresi ("24 saat sonra kapanır") ve geri sayım
- Liste filtreleri: En yeni / En popüler / Kapanmak üzere
- Spam'e karşı rate limit ve basit captcha
- E-posta doğrulama ve "parolamı unuttum"
- Anket kategorileri (yemek, eğlence, alışveriş...)
- Paylaşım için anket önizleme görseli (Open Graph)
- Karanlık mod
