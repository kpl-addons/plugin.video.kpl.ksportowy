# libka
from libka import Plugin, Site, call
from libka.storage import Storage
from libka.logs import log
from libka.menu import Menu

# xbmc
import xbmcgui
import xbmcplugin


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

    def _get_ks(self, endpoint, params={}, headers=None):
        params.update({
            'lang': 'pl',
            'platform': 'ANDROID'
        })
        if endpoint:
            res = self.get(endpoint, params=params, headers=headers)
            log(f'[K-Sportowy] Request made to {res.url} with params: {params}')
            if res.status_code == 200:
                return res.json()
            else:
                return ()

    def _post_ks(self, endpoint, params={}, payload=None):
        params.update({
            'lang': 'pl',
            'platform': 'ANDROID'
        })
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

    def catalog(self):
        return self.make_request('get', '/api/products/sections/main')

    def section(self, id):
        return self.make_request('get', f'/api/products/sections/{id}')

    def serial_section(self, id):
        return self.make_request('get', f'/api/products/vods/serials/{id}/seasons')

    def serial_episode(self, id, e_id):
        return self.make_request('get', f'/api/products/vods/serials/{id}/seasons/{e_id}/episodes')

    def playlist(self, id, type):
        param = {'videoType': type}
        return self.make_request('get', f'/api/products/{id}/videos/playlist', params=param)


def gen_art(data):
    fanart = data.get('16x9')[0]['url']
    if data.get('1x1'):
        return {
            'fanart': fanart,
            'poster': data.get('1x1')[0]['url']
        }
    else:
        return {'fanart': fanart}


def gen_info(data):
    return {'title': data.get('title'), 'plot': data.get('lead')}


class Main(Plugin):
    """K-Sportowy plugin."""

    MENU = Menu(view='addons', items=[
        Menu(title='Biblioteka', call='catalog'),
        Menu(title='Rozkład jazdy', call='noop'),
        Menu(title='Moja lista', call='noop'),
        Menu(title='Ustawienia', call='noop'),
    ])

    def __init__(self):
        super().__init__()
        self.kssite = KSSite()

    def home(self):
        self.menu()
        self.kssite.init()

    def noop(self):
        pass

    def catalog(self):
        data = self.kssite.catalog()

        with self.directory() as kdir:
            for item in data:
                kdir.menu(item['title'], call(self.categories, item['id']))

    def categories(self, id):
        data = self.kssite.section(id)

        with self.directory() as kdir:
            for item in data.get('elements'):
                if item['item']['type'] == 'BANNER':
                    id = item['item']['webUrl'].split(',')[1]
                    kdir.menu(item['item']['title'], call(self.listing, id))
                if item['item']['type'] == 'EPISODE':
                    kdir.play(item['item']['title'], call(self.play_item, item['item']['id']))
                if item['item']['type'] == 'SERIAL':
                    kdir.menu(item['item']['title'], call(self.serial, item['item']['id']))

    def serial(self, id):
        data = self.kssite.serial_section(id)

        with self.directory() as kdir:
            for item in data:
                kdir.menu(item['title'], call(self.serial_episode, id, item['id']))

    def serial_episode(self, id, e_id):
        data = self.kssite.serial_episode(id, e_id)

        with self.directory() as kdir:
            for item in data:
                kdir.play(item['title'], call(self.play_item, item['id']))

    def listing(self, id):
        data = self.kssite.section(id)

        with self.directory() as kdir:
            for item in data.get('elements'):
                kdir.play(item['item']['title'], call(self.play_item, item['item']['id']))

    def play_item(self, id):
        data = self.kssite.playlist(id, 'MOVIE')

        lic = data.get('drm')['WIDEVINE']['src']
        lic = lic + '|Content-Type=application/octet-stream|R{SSM}|'

        if data.get('sources')['DASH'][0]['src'].startswith('//'):
            src = 'https:' + data.get('sources')['DASH'][0]['src']
            if src.endswith('Manifest.ism?indexMode'):
                src = src + '/.mpd'
        else:
            src = data.get('sources')['DASH'][0]['src']
            if src.endswith('Manifest.ism?indexMode'):
                src = src + '/.mpd'

        self.player(source=src, drm='com.widevine.alpha', protocol='mpd', license=lic)

    def player(self, source, drm, protocol, license):
        from inputstreamhelper import Helper  # pylint: disable=import-outside-toplevel

        is_helper = Helper(protocol, drm=drm)
        if is_helper.check_inputstream():
            listitem = xbmcgui.ListItem(path=source)
            listitem.setContentLookup(False)
            listitem.setProperty("IsPlayable", "true")
            listitem.setProperty('inputstream', 'inputstream.adaptive')
            listitem.setProperty('inputstream.adaptive.manifest_type', protocol)
            listitem.setProperty('inputstream.adaptive.license_type', drm)
            listitem.setProperty('inputstream.adaptive.license_key', license)

            xbmcplugin.setResolvedUrl(self.handle, True, listitem=listitem)


# DEBUG ONLY
import sys  # noqa

log(f'K-Sportowy: {sys.argv}')

# Create and run plugin.
Main().run()
