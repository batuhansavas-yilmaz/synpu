# Synpu — PC Durum Paneli: Tasarım Belgesi

Tarih: 2026-10-17
Durum: Onaylandı (kullanıcıyla birebir görüşme sonucu)

## Amaç (neden)

Kullanıcı PC'deki anlık durumu (CPU/GPU kullanımı ve sıcaklıkları, RAM, FPS)
oyun oynarken veya başka bir iş yaparken **telefonundan** görmek istiyor.
PC'deki mevcut araçlar (MSI Center, NVIDIA App) bu veriyi gösteriyor ama
başka cihazlardan erişilebilen bir arayüz sunmuyor ve programatik erişim
API'si açmıyor. Çözüm: PC'de çalışan çok küçük bir yerel web sunucusu ve
telefonun tarayıcısından açılan tek sayfalık panel.

## Hedefler

- PC'de çalışan minik sunucu; aynı yerel ağdaki herhangi bir tarayıcıdan
  erişilebilir. İnternet gerekmez; internetli/internetsiz fark etmez.
- **Yalnızca anlık değerler** (yaklaşık 1 saniyede bir tazelenir). Grafik,
  geçmiş, kayıt yok.
- Gösterilecek veriler:
  - CPU: kullanım % + sıcaklık
  - GPU: kullanım %, sıcaklık, VRAM kullanımı, güç (watt)
  - RAM: kullanılan/toplam + %
  - FPS: oyun çalışırken oyun adı + FPS; oyun yokken "—"
- Çoklu PC desteği: aynı uygulama her PC'ye kurulur. Telefondaki sayfada
  "+ PC ekle" ile adres eklenir, sayfa listeyi tarayıcıda saklar ve
  sekmeler halinde gösterir. PC'ler birbirini tanımak zorunda değildir.
- PC tarafında "Telefonla bağlan" penceresi: o anki adresi ve **QR kodu**
  gösterir; ağ/IP değişince kendini günceller.
- PC'yi yormayan hafiflik: saniyelik birkaç küçük sensör sorgusu.
- Uygulamanın adı **Synpu**. Proje klasörü `C:\Users\batuh\synpu`.
  Varsayılan port **8787**.

## Hedef Olmayanlar (kapsam dışı)

- PIN/şifre yok (kullanıcı kararı; yalnızca kendisi kullanacak, ev ağı).
  Bilinen sonuç: aynı ağdaki biri de adresi açarsa görebilir — kabul edildi.
- Grafik/geçmiş/zaman serisi yok.
- Bulut yok, hesap yok, telemetri yok.
- MSI Center / NVIDIA App entegrasyonu yok (erişilebilir API'leri yok).
  Veriler doğrudan kaynaktan okunur.
- Kamerayla sayfa içinden QR okutma yok (v1). QR, telefon kamerasıyla
  okutulup tarayıcıda açılır; adres elle de girilebilir.
- Oyun dışı uygulamaların FPS'i yok; FPS yalnızca kare sunan oyunlar için
  anlamlıdır.

## Anti-Hedefler (başarısızlık sayılır)

- PC'de gözle görülür kaynak tüketimi (kullanıcı bu konuda hassas).
- Kurulumun karmaşıklığı: her açılışta UAC penceresi, elle başlatma
  gereksinimi vb. olmamalı.
- Ağ değişince telefondan erişimin kaybolup bir daha bulunamaması.

## Kararlar (kullanıcıyla birlikte verilen)

- Veri kaynakları:
  - GPU: NVIDIA sürücü arayüzü (pynvml / nvidia-smi). NVIDIA App'in de
    kullandığı kaynak.
  - CPU % ve RAM: psutil (Windows sayaçları).
  - CPU sıcaklığı: LibreHardwareMonitorLib (açık kaynak; **yönetici izni
    gerektirir**).
  - FPS: PresentMon (Intel'in açık kaynak aracı; **yönetici izni
    gerektirir**).
- Sunucu: Python + FastAPI; WebSocket ile saniyelik push; bağlantı
  koparsa otomatik periyodik sorgulamaya (poll) düşer. CORS açık
  (telefondaki tek sayfa birden çok PC'ye bağlanabilsin diye).
  `0.0.0.0:8787` üzerinde dinler.
- Ön yüz: tek, mobil uyumlu, koyu temalı HTML sayfası. Kartlar + çoklu PC
  için üstte sekmeler. "+ PC ekle" ile adres girilir; liste tarayıcıda
  (localStorage) kalıcıdır. PWA olarak ana ekrana eklenebilir.
- QR penceresi: tkinter mini pencere + qrcode; adresi 30 sn'de bir
  kontrol eder, değişince QR'ı günceller.
- Yönetici izni: Görev Zamanlayıcısı ile "oturum açılışında, en yüksek
  yetkiyle" sessiz başlatma — her seferinde UAC çıkmaz.
- Güvenlik duvarı: ilk kurulumda 8787 için bir kez gelen (inbound) izin
  kuralı eklenir.
- Python: önce sistemdeki 3.14 denenir; bir paket uyumsuzsa uv ile 3.12
  sanal ortamına düşülür.

## Kısıtlar

- Windows 11; RTX 4070 SUPER (12 GB), i5-13500, 34 GB RAM, mevcut.
- CPU sıcaklığı ve FPS için yönetici hakları zorunlu (çözüm yukarıda).
- Telefonun PC'ye erişmesi için ikisinin aynı ağda olması gerekir;
  router'da istemci izolasyonu (client isolation) kapalı olmalı.

## Doğrulama Kriterleri

- Telefondan panele bağlanılır; değerler NVIDIA App / MSI Center
  değerleriyle tutarlıdır (sıcaklık ±1-2 °C tolerans).
- Bir oyun açıkken oyun adı ve FPS görünür; oyun kapalıyken "—" görünür.
- İkinci bir kopya (farklı port) ile çoklu PC akışı denenir; sekme
  geçişi ve "+ PC ekle" çalışır.
- Ağ değişimi senaryosu: QR penceresi güncel adresi gösterir.
- PC kaynak kullanımı: uygulama boşta gözle görülür yük bindirmez.

## Uygulayıcıya Bırakılanlar (builder'ın kararı)

- Proje yapısı, modül organizasyonu, kütüphane sürümleri.
- PresentMon'un çalıştırılma/örnekleme biçimi (sürekli süreç, çıktı
  ayrıştırma) ve "oyun yok" tespiti.
- LibreHardwareMonitorLib entegrasyonu ve başarısızlıkta WMI yedeği.
- API şeması (JSON alan adları), hata durumları, yeniden bağlanma
  stratejisi ayrıntıları.
- Test yaklaşımı (birim testleri + elle uçtan uca testler).
- Kurulum betikleri (görev zamanlayıcı, güvenlik duvarı) ve README.
- Sayfanın görsel yerleşimi (kart düzeni, tipografi).
