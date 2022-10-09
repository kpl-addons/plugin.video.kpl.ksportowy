# libka
from libka import Plugin, Site, call
from libka.storage import Storage
from libka.logs import log
from libka.menu import Menu

# xbmc
import xbmcgui


class KSSite(Site):
    """K-Sportowy API."""

    def __init__(self, base='https://kanalsportowy.pl', *args, verify_ssl=False, **kwargs):
        super().__init__(base, *args, verify_ssl=verify_ssl, **kwargs)

        self.storage = Storage('data.json', addon=None, sync=True)
            
        self.headers = {
            'api-deviceinfo': 'Phone android;30;android;sdk_gphone_x86;google;1.0.0.24;',
            'accept-encoding': 'gzip',
            'user-agent': 'okhttp/4.9.1 ',
            'cookie': 'AWSALBAPP-0=_remove_; AWSALBAPP-1=_remove_; AWSALBAPP-2=_remove_; AWSALBAPP-3=_remove_'
        }

    def _get_ks(self, endpoint, params, headers=None):
        params = {
            'lang': 'pl',
            'platform': 'ANDROID'
        }
        if endpoint:
            res = self.get(endpoint, params=params, headers=headers)
            log(f'[K-Sportowy] Request made to {res.url} with params: {params}')
            if res.status_code == 200:
                return res.json()
            else:
                return ()
            
    def _post_ks(self, endpoint, params, payload):
        params = {
            'lang': 'pl',
            'platform': 'ANDROID'
        }
        if endpoint:
            res = self.post(endpoint, params=params, json=payload)
            log(f'[K-Sportowy] Request made to {res.url} with params: {params}')
            if res.status_code == 200:
                return res.json()
            else:
                return ()

    def make_request(self, method, endpoint, params={}, payload={}, headers=None):
        if method == 'get':
            return self._get_ks(endpoint, params, headers)
        if method == 'post':
            return self._post_ks(endpoint, params, payload)
        
    def init(self):
        if self.storage.get('username') and self.storage.get('password'):
            self.check_login()
        else:
            email = xbmcgui.Dialog().input('Podaj swój email', type=xbmcgui.INPUT_ALPHANUM)
            password = xbmcgui.Dialog().input('Podaj swoje hasło', type=xbmcgui.INPUT_ALPHANUM, 
                                              option=xbmcgui.ALPHANUM_HIDE_INPUT)
            self.storage.set('username', email)   
            self.storage.set('password', password)
            
    def check_login(self):
        self.headers.update({
            'api-authentication': str(self.storage.get('token')),
            'api-profileuid': str(self.storage.get('profile_id'))
        })
        res = self.make_request('get', '/api/subscribers/detail', headers=self.headers)
        if res:
            return True
        else:
            self.login(self.storage.get('username'), self.storage.get('password'))
            
    def login(self, username, password):
        payload = {
            "auth": {
            "type": "PASSWORD",
            "value": password
        },
        "email": username,
        "rememberMe": True
        }
        userdata = self.make_request('post', '/api/subscribers/login', payload=payload)
        
        if userdata and userdata.get('token'):
            self.storage.set('token', userdata['token'])
            self.storage.set('profile_id', userdata['activeProfileId'])
            self.storage.save()
        else:
            xbmcgui.Dialog().notification('K-Sportowy', 'Niezalogowano. Dostęp może być ograniczony.')


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

    def home(self):
        self.menu()
        self.kssite.init()

    def noop(self):
        pass


# DEBUG ONLY
import sys  # noqa

log(f'K-Sportowy: {sys.argv}')

# Create and run plugin.
Main().run()
