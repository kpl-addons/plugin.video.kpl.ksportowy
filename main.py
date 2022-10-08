# libka
from libka import Plugin, Site, call
from libka.storage import Storage
from libka.logs import log
from libka.menu import Menu


class KSSite(Site):
    """K-Sportowy API."""

    def __init__(self, base='https://kanalsportowy.pl/api', *args, verify_ssl=False, **kwargs):
        super().__init__(base, *args, verify_ssl=verify_ssl, **kwargs)

        self.storage = Storage('data.json', addon=None)

    def _get_ks(self, endpoint, params={}):
        params = {
            'lang': 'pl',
            'platform': 'ANDROID'
        }
        if endpoint:
            res = self.get(endpoint, params=params)
            if res.status_code == 200:
                log(f'[K-Sportowy] Request made to {res.url} with params: {params}')
                return res.json()
            else:
                return ()

    # def make_request(self, key, params=None, **kwargs):
    #     if key in TMDB_LINKS(**kwargs):
    #         return self._get_tmdb(TMDB_LINKS(**kwargs)[key], params)


class Main(Plugin):
    """K-Sportowy plugin."""

    MENU = Menu(view='addons', items=[
        Menu(title='Biblioteka', call='nop'),
        Menu(title='Rozkład jazdy', call='nop'),
        Menu(title='Moja lista', call='nop'),
        Menu(title='Ustawienia', call='nop'),
    ])

    def __init__(self):
        super().__init__()
        self.kssite = KSSite()
        self.headers = {
            'authorization': 'Basic cmVkZ2U6NHRFNzNqUmdIaFBuVDNweA== ',
            'api-deviceinfo': 'Phone android;30;android;sdk_gphone_x86;google;1.0.0.24;',
            'accept-encoding': 'gzip',
            'user-agent': 'okhttp/4.9.1 ',
            'cookie': 'AWSALBAPP-0=_remove_; AWSALBAPP-1=_remove_; AWSALBAPP-2=_remove_; AWSALBAPP-3=_remove_'
        }
        try:
            self.username = self.user_data.get('username')
            self.password = self.user_data.get('password')
        except TypeError:
            self.username = ''
            self.password = ''

    def home(self):
        self.menu()

    def noop(self):
        pass
    
    def device_uid():
        return 


# DEBUG ONLY
import sys  # noqa

log(f'K-Sportowy: {sys.argv}')

# Create and run plugin.
Main().run()
