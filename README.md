# Synpu

PC'nin canlı sistem istatistiklerini (CPU/GPU kullanımı ve sıcaklığı, RAM, oyun FPS) telefonundan takip et. Synpu PC'de arka planda çalışır; aynı Wi-Fi ağındaki telefon tarayıcısından `http://<PC-IP>:8787` adresine bağlanırsın. Kurulum ve hesap gerekmez, veri internete gitmez — her şey yerel ağda kalır.

## Ne gösterir?

| Kart | Değerler |
|------|----------|
| İşlemci | Kullanım %, sıcaklık (yönetici izniyle) |
| Ekran Kartı | Kullanım %, sıcaklık, VRAM, güç (NVIDIA) |
| Bellek | Kullanılan / toplam, % |
| Oyun FPS | Aktif oyunun anlık FPS değeri (yönetici izniyle) |

Değer saniyede bir güncellenir. Okunamayan bir değer `—` olarak görünür (ör. NVIDIA kart yoksa GPU, oyun açık değilse FPS).

## Gereksinimler

- Windows 10/11
- Yönetici izni (CPU sıcaklığı ve FPS için gerekli; kurulum bunu otomatik ayarlar)
- NVIDIA ekran kartı (opsiyonel — yoksa GPU kartı `—` gösterir)
- Telefonla aynı Wi-Fi ağı

## Kurulum

1. Bu klasörü PC'ye indir (ZIP'i çıkar veya `git clone`).
2. `setup.bat` dosyasına çift tıkla ve UAC onayını ver.
3. Kurulum biter: bağımlılıklar indirilir, güvenlik duvarı kuralı eklenir ve Synpu otomatik başlar. Her açılışta kendiliğinden çalışır.

Kurulum sırasında internetten indirilenler: [uv](https://astral.sh/uv) (Python paket yöneticisi), [PresentMon v2.6.0](https://github.com/GameTechDev/PresentMon) (FPS ölçümü) ve [LibreHardwareMonitor v0.9.6](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (CPU sıcaklığı). Kapalı kaynak hiçbir bileşen yoktur.

## Telefonla bağlanma

1. Kurulum sonrası PC'de **"Synpu — Telefonla Bağlan"** penceresi açılır; QR kodu telefonun kamerasıyla okut.
2. Tarayıcı otomatik açılır ve panel görünür.
3. Sayfayı ana ekrana ekleyebilirsin (Tarayıcı menüsü → "Ana ekrana ekle") — uygulama gibi açılır.

Pencereyi kapatırsan Synpu çalışmaya devam eder; sağ alt tepsi simgesinden "QR'ı Göster" ile geri açabilirsin.

## Çoklu PC

Aynı uygulamayı diğer PC'lere de kur. Telefon sayfasındaki **"+ PC ekle"** düğmesiyle diğer PC'nin adresini (`http://192.168.1.50:8787` gibi) ekle; üstteki sekmelerden PC'ler arasında geçiş yap.

## Sorun giderme

- **CPU sıcaklığı / FPS `—` görünüyor:** Uygulama yönetici olarak çalışmıyor olabilir. `Get-ScheduledTask -TaskName Synpu` görevinin çalıştığını kontrol et; kurulum görevi yönetici seviyesinde ayarlar.
- **Telefondan bağlanamıyorum:** Telefon ve PC aynı Wi-Fi'de mi? Ağ profilinin **Özel (Private)** olması gerekir; genel ağda Windows gelen bağlantıları engeller. Güvenlik duvarı kuralı: `Get-NetFirewallRule -DisplayName "Synpu*"`.
- **"Port 8787 kullanımda" hatası:** Synpu zaten çalışıyor olabilir. Farklı port için: `$env:SYNPU_PORT=8788; .venv\Scripts\pythonw.exe -m synpu`
- **GPU değerleri `—`:** NVIDIA sürücüsü yok ya da kart NVIDIA değil.
- **Adres değişti:** Modem PC'ye yeni IP verdiyse QR penceresindeki adres güncellenir; telefon sayfasındaki sekmeyi silip yeniden ekle.

## Kaldırma

```powershell
Unregister-ScheduledTask -TaskName Synpu -Confirm:$false
Remove-NetFirewallRule -DisplayName "Synpu (TCP 8787)"
```

Sonra klasörü sil. (İsteğe bağlı: `%LOCALAPPDATA%\Synpu` klasörünü de silebilirsin.)

## Lisanslar

- Synpu: [MIT](LICENSE)
- [PresentMon](https://github.com/GameTechDev/PresentMon): MIT — metin: `third_party/PresentMon-LICENSE.txt`
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor): MPL-2.0 — metin: `third_party/LibreHardwareMonitor-LICENSE.txt`
- Python bağımlılıkları (FastAPI, uvicorn, psutil, pythonnet, qrcode, pystray, Pillow): MIT/BSD/Apache-2.0
- Sunucu tarafına kurulan `LibreHardwareMonitorLib.dll` ve `PresentMon.exe` bu depoda değildir; kurulum betiği indirir.

---

## English (short)

Synpu shows live CPU/GPU usage and temperature, RAM, and game FPS of your PC in your phone's browser over the local network — no account, no cloud. Requirements: Windows 10/11, admin rights (for CPU temp and FPS). Setup: double-click `setup.bat`, approve UAC, then scan the QR code shown on the PC with your phone (same Wi-Fi). Multi-PC: add other PCs from the "+ PC ekle" button. Uninstall: remove the "Synpu" scheduled task, the "Synpu (TCP 8787)" firewall rule, and the folder. License: MIT.
