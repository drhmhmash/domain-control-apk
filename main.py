import json
import socket
import ssl
import urllib.error
import urllib.request
import webbrowser

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

Window.clearcolor = (0.08, 0.10, 0.14, 1)


class DomainManagerUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=10, **kwargs)

        title = Label(
            text="لوحة تحكم الدومين",
            font_size="20sp",
            bold=True,
            size_hint_y=None,
            height=45,
        )
        self.add_widget(title)

        self.domain_input = TextInput(
            text="drhm.cu.ma",
            hint_text="أدخل اسم الدومين مثال: drhm.cu.ma",
            multiline=False,
            size_hint_y=None,
            height=45,
        )
        self.add_widget(self.domain_input)

        row1 = BoxLayout(size_hint_y=None, height=48, spacing=8)
        btn_ip = Button(text="فحص IP الدومين", background_color=(0.15, 0.45, 0.85, 1))
        btn_ip.bind(on_press=self.check_ip)

        btn_ssl = Button(text="فحص شهادة SSL", background_color=(0.12, 0.62, 0.42, 1))
        btn_ssl.bind(on_press=self.check_ssl)

        row1.add_widget(btn_ip)
        row1.add_widget(btn_ssl)
        self.add_widget(row1)

        self.zone_id = TextInput(
            hint_text="Cloudflare Zone ID",
            multiline=False,
            size_hint_y=None,
            height=42,
        )
        self.record_id = TextInput(
            hint_text="DNS Record ID",
            multiline=False,
            size_hint_y=None,
            height=42,
        )
        self.api_token = TextInput(
            hint_text="Cloudflare API Token",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=42,
        )

        row2 = BoxLayout(size_hint_y=None, height=42, spacing=8)
        self.rec_type = TextInput(
            text="TXT",
            hint_text="النوع (A / TXT)",
            multiline=False,
            size_hint_x=0.3,
        )
        self.rec_name = TextInput(
            text="_acme-challenge",
            hint_text="اسم السجل",
            multiline=False,
            size_hint_x=0.7,
        )
        row2.add_widget(self.rec_type)
        row2.add_widget(self.rec_name)

        self.rec_content = TextInput(
            hint_text="قيمة السجل الجديدة (IP أو نص TXT)",
            multiline=False,
            size_hint_y=None,
            height=42,
        )

        btn_update_dns = Button(
            text="تحديث سجل DNS الآن",
            size_hint_y=None,
            height=46,
            background_color=(0.85, 0.50, 0.10, 1),
        )
        btn_update_dns.bind(on_press=self.update_cloudflare_dns)

        self.panel_url = TextInput(
            text="https://googiehost.com:2222",
            hint_text="رابط لوحة التحكم",
            multiline=False,
            size_hint_y=None,
            height=42,
        )
        btn_open_panel = Button(
            text="فتح لوحة التحكم",
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

        scroll = ScrollView(size_hint_y=1)
        self.output_label = Label(
            text="النتائج ستظهر هنا...",
            font_size="14sp",
            halign="left",
            valign="top",
            size_hint_y=None,
        )
        self.output_label.bind(
            texture_size=lambda instance, value: setattr(instance, "height", value[1] + 20),
            width=lambda instance, value: setattr(instance, "text_size", (value, None)),
        )
        scroll.add_widget(self.output_label)
        self.add_widget(scroll)

    def set_result(self, text):
        Clock.schedule_once(lambda dt: setattr(self.output_label, "text", text))

    def check_ip(self, instance):
        domain = self.domain_input.text.strip()
        if not domain:
            self.set_result("يرجى إدخال اسم الدومين أولاً.")
            return
        try:
            ip = socket.gethostbyname(domain)
            self.set_result(f"الدومين: {domain}\nعنوان IP الحالي: {ip}")
        except Exception as e:
            self.set_result(f"تعذر جلب IP للدومين ({domain}):\n{e}")

    def check_ssl(self, instance):
        domain = self.domain_input.text.strip()
        if not domain:
            self.set_result("يرجى إدخال اسم الدومين أولاً.")
            return
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=8) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    subject = dict(x[0] for x in cert.get("subject", []))
                    not_after = cert.get("notAfter", "غير متوفر")
                    self.set_result(
                        f"شهادة SSL فعالة على: {domain}\n"
                        f"Subject CN: {subject.get('commonName', '-')}\n"
                        f"Issuer O: {issuer.get('organizationName', '-')}\n"
                        f"تاريخ الانتهاء: {not_after}"
                    )
        except Exception as e:
            self.set_result(f"تعذر فحص SSL للدومين ({domain}):\n{e}")

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

        url = f"https://api.cloudflare.com/client/v4/zones/{zone}/dns_records/{rec_id}"
        payload = json.dumps(
            {
                "type": rtype,
                "name": rname,
                "content": rcontent,
                "ttl": 120,
                "proxied": False,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            method="PATCH",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    self.set_result(f"تم تحديث سجل {rtype} ({rname}) بنجاح إلى:\n{rcontent}")
                else:
                    self.set_result(f"فشل التحديث:\n{data}")
        except urllib.error.HTTPError as e:
            self.set_result(f"خطأ HTTP ({e.code}):\n{e.read().decode('utf-8', errors='ignore')}")
        except Exception as e:
            self.set_result(f"خطأ أثناء الاتصال بـ Cloudflare:\n{e}")

    def open_panel(self, instance):
        url = self.panel_url.text.strip()
        if url:
            webbrowser.open(url)


class DomainPanelApp(App):
    def build(self):
        self.title = "Domain Control"
        return DomainManagerUI()


if __name__ == "__main__":
    DomainPanelApp().run()
