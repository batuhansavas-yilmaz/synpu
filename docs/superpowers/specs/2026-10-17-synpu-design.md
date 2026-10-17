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

Ayrıca kullanıcı bu uygulamayı eş, dost ve arkadaşlarıyla paylaşıp onların
da kendi PC'lerinde kullanmasını istiyor. Bu yüzden kurulumun kolay,
belgelerin anlaşılır ve projenin açık kaynak olması gerekiyor.

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
- Açık kaynak, GitHub: https://github.com/batuhansavas-yilmaz/synpu

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
- Arkadaşların kurulumda takılıp bırakması.

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
  koparsa otomatik periyodik sorgulamaya (poll) düşer. CORS politikası
  için "Denetim Sonrası Netleşen Kararlar"a bakınız.
  `0.0.0.0:8787` üzerinde dinler.
- Ön yüz: tek, mobil uyumlu, koyu temalı HTML sayfası. Kartlar + çoklu PC
  için üstte sekmeler. "+ PC ekle" ile adres girilir; liste tarayıcıda
  (localStorage) kalıcıdır. Telefondan "Ana ekrana ekle" kısayolu
  desteklenir (gerçek PWA/HTTPS v1'de yok).
- QR penceresi: tkinter mini pencere + qrcode; adresi 30 sn'de bir
  kontrol eder, değişince QR'ı günceller.
- Yönetici izni: Görev Zamanlayıcısı ile "oturum açılışında, en yüksek
  yetkiyle" sessiz başlatma — her seferinde UAC çıkmaz.
- Güvenlik duvarı: ilk kurulumda 8787 için bir kez gelen (inbound) izin
  kuralı eklenir.
- Python: uv ile sabit Python 3.12 kullanılır (her makinede aynı sürüm —
  uyumluluk garantisi).

## Dağıtım ve Paylaşım (eş dost için)

- Proje açık kaynak: https://github.com/batuhansavas-yilmaz/synpu (public).
- Herkes kendi PC'sine kurar. Kurulum "tek tuş": `setup.bat` (arkasında
  PowerShell betiği); uv ile Python 3.12 + bağımlılıkları kurar, sabit
  sürümlü PresentMon (Intel GitHub release) ile LibreHardwareMonitorLib
  DLL'ini indirir, güvenlik duvarı kuralını ve Görev Zamanlayıcı kaydını
  oluşturur.
- Hedef sistem: Windows 10/11 x64, NVIDIA GPU. CPU sıcaklığı çoğu
  anakartta okunur; okunamayan sensörlerde kart "—" gösterir.
- README Türkçe (arkadaşlar için) + kısa İngilizce hızlı başlangıç.
- Lisans: Synpu MIT; üçüncü taraf bileşenlerin lisans dosyaları
  (PresentMon MIT, LibreHardwareMonitorLib MPL-2.0) depoda bulunur.
- Çalışma zamanında internet gerekmez; yalnızca ilk kurulum indirme için
  internet ister.

## Denetim Sonrası Netleşen Kararlar (builder)

- "PWA" v1'de gerçek PWA değil: HTTP üzerinden mobil sayfa; "Ana ekrana
  ekle" kısayolu yeterli. HTTPS + service worker + yerel sertifika işleri
  v2'ye bırakıldı.
- QR adres seçimi: birincil adres = varsayılan ağ geçidi olan etkin
  arayüzün IPv4 adresi; sanal adaptörler (Hyper-V, WSL, VPN) dışlanır.
  Başka aday adresler varsa pencere bunları da listeler.
- QR penceresi yaşam döngüsü: uygulama tepsi simgesi olarak çalışır;
  pencere tepsi tıklamasıyla açılıp kapanır; ilk çalıştırmada bir kez
  otomatik açılır. Otomatik başlatma sessizdir (UAC yok, tray'de).
- CORS/Origin politikası: yalnızca özel ağ kaynakları (192.168.x, 10.x,
  172.16-31.x) ve localhost kabul edilir; public siteler veriyi okuyamaz.
  WebSocket bağlantılarında da aynı Origin kontrolü uygulanır.
- Kimlik doğrulama v1'de yok (kullanıcı kararı). Aynı ağdaki başkaları
  paneli görebilir; kabul edildi.

## Kısıtlar

- Windows 10/11 x64; RTX 4070 SUPER (12 GB), i5-13500, 34 GB RAM mevcut
  geliştirme makinesi. Paylaşılan arkadaşlar için gereksinim: Windows +
  NVIDIA GPU.
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
- Temiz kurulum: `setup.bat` temiz bir sistemde (veya ikinci bir klasörde)
  baştan sona sorunsuz çalışır; kurulum sonrası uygulama kendiliğinden
  açılıp panel telefondan görünür.

## Uygulayıcıya Bırakılanlar (builder'ın kararı)

- Proje yapısı, modül organizasyonu, kütüphane sürümleri.
- PresentMon'un çalıştırılma/örnekleme biçimi (sürekli süreç, çıktı
  ayrıştırma) ve "oyun yok" tespiti.
- LibreHardwareMonitorLib entegrasyonu ve başarısızlıkta WMI yedeği.
- API şeması (JSON alan adları), hata durumları, yeniden bağlanma
  stratejisi ayrıntıları.
- Test yaklaşımı (birim testleri + elle uçtan uca testler).
- Kurulum betiklerinin (setup.bat, görev zamanlayıcı, güvenlik duvarı)
  ayrıntıları ve README içeriği.
- Sayfanın görsel yerleşimi (kart düzeni, tipografi).
