# Köçür Pro — idarəetmə sistemi

Telefon və kompüter brauzerləri üçün Flask + SQLite veb-tətbiqi. İlkin versiyada Azərbaycan/Rus dili, rollara əsaslanan giriş, sifarişlər, müştərilər, tərəfdaşlar, ödənişlər, xərclər, aylıq hesabatlar, CSV ixracı və administrator ehtiyat nüsxəsi mövcuddur.

## 1. Tələblər
- Python 3.10+
- İnternet yalnız Python paketlərini quraşdırmaq üçün lazımdır; tətbiq özü lokal işləyə bilər.

## 2. Lokal quraşdırma

### Windows
1. ZIP-i qovluğa çıxarın.
2. Həmin qovluqda terminal/CMD açın.
3. Bu əmrləri icra edin:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```
4. Brauzerdə `http://127.0.0.1:5000/setup` açın.
5. Öz administrator login və parolunuzu yaradın. Parol minimum 12 simvol olmalıdır.

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```
Sonra `http://127.0.0.1:5000/setup` ünvanını açın.

İlk administrator yaradılandan sonra `/setup` yeni hesab yaratmır, giriş səhifəsinə yönləndirir. Tətbiqi bağlamaq üçün terminalda `Ctrl+C` basın.

## 3. Rollar
- **Administrator:** bütün bölmələr, istifadəçilər və ehtiyat nüsxə.
- **Menecer:** sifariş statusu, müştəri, tərəfdaş, maliyyə və hesabatlar.
- **İşçi:** sifariş və müştərilərə baxış; maliyyə və istifadəçi idarəetməsinə giriş yoxdur.

## 4. Məlumatların saxlanması
İlkin verilənlər bazası `data/kocur_pro.sqlite3` faylında saxlanır. Tətbiq ilk işə düşəndə `data/.secret_key` yaradır. Bu qovluğu silməyin və başqaları ilə paylaşmayın. `KOCUR_DATA_DIR` və `KOCUR_DB_PATH` mühit dəyişənləri ilə verilənlər bazasının yerini dəyişmək olar.

Administrator panelindən **Ehtiyat nüsxə** bölməsinə keçib SQLite nüsxəsini endirin. Ehtiyat fayllarını şifrələnmiş və məhdud girişli yerdə saxlayın. Testdən sonra nüsxəni ayrıca cihazda bərpa etməyi yoxlamaq məsləhətdir.

## 5. Vacib məhdudiyyətlər
- Bu, ilkin MVP-dir; kodu öz serverinizə yerləşdirmədən əvvəl sınaqdan keçirin.
- `python app.py` lokal istifadə üçün `127.0.0.1` ünvanında işləyir. Başqa cihazlardan və internetdən istifadə üçün ayrıca hostinq, WSGI server (məsələn Waitress/Gunicorn), HTTPS reverse proxy, firewall, güclü `KOCUR_SECRET_KEY`, müntəzəm backup və server yeniləmələri lazımdır.
- İctimai serverdə `COOKIE_SECURE=1` qurun və HTTPS istifadə edin. `KOCUR_SECRET_KEY` mühit dəyişəninə uzun, təsadüfi dəyər verin.
- SQLite bir kompüterdə və kiçik həcmdə istifadə üçün münasibdir. Eyni anda çox istifadəçi işləyəndə PostgreSQL və ayrıca deploy konfiqurasiyasına keçmək daha uyğundur.
- Bu tətbiq rəsmi vergi/mühasibat proqramını və qanuni hesabat öhdəliklərini əvəz etmir. Maliyyə rəqəmlərini rəsmi uçotla tutuşdurun.
- Müştəri və işçi məlumatları şəxsi məlumatdır. Yalnız zəruri məlumatları saxlayın, girişləri məhdudlaşdırın və yerli qanunvericiliyə əməl edin.

## 6. Əsas hesablamalar
- Dashboard gəliri yalnız `customer` tipli faktiki daxil edilmiş ödənişlərdən hesablayır.
- Tərəfdaş ödənişləri `partner` tipli əməliyyatlar kimi daxil edilir.
- Komissiya ayrıca `commission` ödəniş növüdür; aylıq hesabatda göstərilir.
- Müştəri və tərəfdaş borcu sifarişdəki razılaşdırılmış məbləğdən həmin sifariş üçün qeydə alınmış ödənişləri çıxmaqla hesablanır.
- İlkin fərq = faktiki müştəri ödənişləri − tərəfdaş ödənişləri − qeydə alınmış xərclər. Bu, vergi və digər bütün öhdəliklərdən sonrakı xalis mənfəət kimi qəbul edilməməlidir.
