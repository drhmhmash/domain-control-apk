import socket
import ssl
import json
import threading
import webbrowser
import urllib.request
import urllib.error

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False

FONT_PATH = "fonts/arabic.ttf"


def fix_ar(text):
    if not text:
        return ""
    s = str(text)
    if not HAS_ARABIC:
        return s
    try:
        reshaped = arabic_reshaper.reshape(s)
        return get_display(reshaped)
    except Exception:
        return s


def ar(text):
    return fix_ar(text)


class DomainControlLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=12, spacing=8, **kwargs)

        title_label = Label(
            text=fix_ar("لوحة التحكم بالدومين - drhm.cu.ma"),
            font_name=FONT_PATH,
            size_hint_y=None,
            height=44,
        )
        self.add_widget(title_label)

        self.domain_input = TextInput(
            text="drhm.cu.ma",
            hint_text="Domain (e.g. drhm.cu.ma)",
            multiline=False,
            size_hint_y=None,
            height=42,
        )
        self.add_widget(self.domain_input)

        row1 = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=46)
        btn_ip = Button(
            text=fix_ar("فحص IP"),
            font_name=FONT_PATH,
            background_color=(0.15, 0.45, 0.85, 1),
        )
        btn_ip.bind(on_press=self.check_ip)

        btn_ssl = Button(
            text=fix_ar("فحص SSL"),
            font_name=FONT_PATH,
            background_color=(0.12, 0.62, 0.42, 1),
        )
        btn_ssl.bind(on_press=self.check_ssl)

        row1.add_widget(btn_ip)
        row1.add_widget(btn_ssl)
        self.add_widget(row1)

        self.zone_id = TextInput(
            text="",
            hint_text="Cloudflare Zone ID",
            multiline=False,
            size_hint_y=None,
            height=40,
        )
        self.record_id = TextInput(
            text="",
            hint_text="Cloudflare Record ID",
            multiline=False,
            size_hint_y=None,
            height=40,
        )
        self.api_token = TextInput(
            text="",
            hint_text="Cloudflare API Token",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=40,
        )

        row2 = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=40)
        self.rec_type = TextInput(
            text="A",
            hint_text="Type (A / CNAME)",
            multiline=False,
        )
        self.rec_name = TextInput(
            text="",
            hint_text="Record Name",
            multiline=False,
        )
        row2.add_widget(self.rec_type)
        row2.add_widget(self.rec_name)

        self.rec_content = TextInput(
            text="",
            hint_text="Record Content (IP / Target)",
            multiline=False,
            size_hint_y=None,
            height=40,
        )

        btn_update_dns = Button(
            text=fix_ar("تحديث DNS"),
            font_name=FONT_PATH,
            size_hint_y=None,
            height=46,
            background_color=(0.85, 0.50, 0.10, 1),
        )
        btn_update_dns.bind(on_press=self.update_cloudflare_dns)

        self.panel_url = TextInput(
            text="https://googiehost.com:2222",
            hint_text="Control Panel URL",
            multiline=False,
            size_hint_y=None,
            height=40,
        )

        btn_open_panel = Button(
            text=fix_ar("فتح لوحة التحكم"),
            font_name=FONT_PATH,
            size_hint_y=None,
            height=46,
            background_color=(0.35, 0.25, 0.75, 1),
        )
        btn_open_panel.bind(on_press=self.open_panel)

        self.add_widget(self.zone_id)
        self.add_widget(self.record_id)
        self.add_widget(self.api_token)
        self.add_widget(row2)
        self.add_widget(self.rec_content)
        self.add_widget(btn_update_dns)
        self.add_widget(self.panel_url)
        self.add_widget(btn_open_panel)

        scroll = ScrollView(size_hint=(1, 1))
        self.output_label = Label(
            text=fix_ar("جاهز للعمل..."),
            font_name=FONT_PATH,
            size_hint_y=None,
            halign="right",
            valign="top",
            text_size=(None, None),
        )
        self.output_label.bind(
            texture_size=lambda inst, val: setattr(inst, "height", val[1] + 20),
            width=lambda inst, val: setattr(inst, "text_size", (val - 10, None)),
        )
        scroll.add_widget(self.output_label)
        self.add_widget(scroll)

    def set_result(self, text):
        Clock.schedule_once(lambda dt: setattr(self.output_label, "text", ar(text)))

    def check_ip(self, instance):
        domain = self.domain_input.text.strip()
        if not domain:
            self.set_result("يرجى إدخال اسم الدومين أولاً.")
            return

        def _worker():
            try:
                ip = socket.gethostbyname(domain)
                self.set_result(f"الدومين: {domain}\nعنوان IP الحالي: {ip}")
            except Exception as e:
                self.set_result(f"تعذر جلب IP للدومين ({domain}):\n{e}")

        threading.Thread(target=_worker, daemon=True).start()

    def check_ssl(self, instance):
        domain = self.domain_input.text.strip()
        if not domain:
            self.set_result("يرجى إدخال اسم الدومين أولاً.")
            return

        def _worker():
            try:
                ctx = ssl.create_default_context()
                with socket.create_connection((domain, 443), timeout=8) as sock:
                    with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        issuer = cert.get("issuer", "")
                        not_after = cert.get("notAfter", "")
                        self.set_result(
                            f"شهادة SSL فعالة للدومين: {domain}\n"
                            f"تاريخ الانتهاء: {not_after}\n"
                            f"الجهة المصدرة: {issuer}"
                        )
            except Exception as e:
                self.set_result(f"تعذر فحص SSL للدومين ({domain}):\n{e}")

        threading.Thread(target=_worker, daemon=True).start()

    def update_cloudflare_dns(self, instance):
        zone = self.zone_id.text.strip()
        rec_id = self.record_id.text.strip()
        token = self.api_token.text.strip()
        rtype = self.rec_type.text.strip().upper()
        rname = self.rec_name.text.strip()
        rcontent = self.rec_content.text.strip()

        if not all([zone, rec_id, token, rtype, rname, rcontent]):
            self.set_result("يرجى تعبئة جميع حقول Cloudflare API وبيانات السجل.")
            return

        def _worker():
            url = f"https://api.cloudflare.com/client/v4/zones/{zone}/dns_records/{rec_id}"
            payload = json.dumps({
                "type": rtype,
                "name": rname,
                "content": rcontent,
                "ttl": 120,
                "proxied": False,
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                method="PUT",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    if data.get("success"):
                        self.set_result(f"تم تحديث سجل {rtype} ({rname}) بنجاح إلى:\n{rcontent}")
                    else:
                        self.set_result(f"فشل التحديث:\n{data}")
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                self.set_result(f"خطأ HTTP ({e.code}):\n{body}")
            except Exception as e:
                self.set_result(f"خطأ أثناء الاتصال بـ Cloudflare:\n{e}")

        threading.Thread(target=_worker, daemon=True).start()

    def open_panel(self, instance):
        url = self.panel_url.text.strip()
        if not url:
            self.set_result("يرجى إدخال رابط لوحة التحكم أولاً.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            webbrowser.open(url)
            self.set_result(f"جاري فتح الرابط:\n{url}")
        except Exception as e:
            self.set_result(f"تعذر فتح الرابط:\n{e}")


class DomainControlApp(App):
    def build(self):
        self.title = "Domain Control"
        return DomainControlLayout()


if __name__ == "__main__":
    DomainControlApp().run()
