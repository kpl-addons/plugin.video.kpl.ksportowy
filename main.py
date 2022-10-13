# libka
from libka import Plugin, Site, call, calendar, subobject
from libka.storage import Storage
from libka.logs import log
from libka.menu import Menu
from libka.format import stylize
from libka.search import Search, search

# xbmc
import xbmcgui
import xbmcplugin

# common imports
import datetime


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

    def _get_ks(self, endpoint, params=None, headers=None):
        if not params:
            params = {}
        params.update({
            'lang': 'pl',
            'platform': 'ANDROID'
        })
        if endpoint:
            return self.jget(endpoint, params=params, headers=headers)

    def _post_ks(self, endpoint, params=None, payload=None, headers=None):
        if not params:
            params = {}
        params.update({
            'lang': 'pl',
            'platform': 'ANDROID'
        })
        if endpoint:
            return self.post(endpoint, params=params, json=payload, headers=headers)

    def _delete_ks(self, endpoint, params=None, headers=None):
        if not params:
            params = {}
        params.update({
            'lang': 'pl',
            'platform': 'ANDROID'
        })
        if endpoint:
            return self.delete(endpoint, params=params, headers=headers)

    def make_request(self, method, endpoint, params=None, payload=None, headers=None):
        if method == 'get':
            return self._get_ks(endpoint, params, headers)
        if method == 'post':
            return self._post_ks(endpoint, params, payload, headers)
        if method == 'delete':
            return self._delete_ks(endpoint, params, headers)

    def init(self):
        if self.storage.get('credentials'):
            self.check_login()
        else:
            email = xbmcgui.Dialog().input('Podaj swój email', type=xbmcgui.INPUT_ALPHANUM)
            password = xbmcgui.Dialog().input('Podaj swoje hasło', type=xbmcgui.INPUT_ALPHANUM,
                                              option=xbmcgui.ALPHANUM_HIDE_INPUT)
            self.storage.set('credentials', {
                'email': email,
                'pass': password
            })

    def check_login(self):
        self.headers.update({
            'api-authentication': str(self.storage.get('token')),
            'api-profileuid': str(self.storage.get('profile_id'))
        })
        res = self.make_request('get', '/api/subscribers/detail', headers=self.headers)
        if res.get('code') == 'AUTHENTICATION_REQUIRED':
            return self.login(self.storage.get('credentials')['email'], self.storage.get('credentials')['pass'])
        else:
            return True

    def login(self, username, password):
        payload = {
            "auth": {
                "type": "PASSWORD",
                "value": password
            },
            "email": username,
            "rememberMe": True
        }
        userdata = self.make_request('post', '/api/subscribers/login', payload=payload).json()

        if userdata and userdata.get('token'):
            self.storage.set('user_data', {
                'token': userdata.get('token'),
                'profile_id': userdata.get('activeProfileId')
            })
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

    def playlist(self, id, v_type):
        param = {'videoType': v_type}
        return self.make_request('get', f'/api/products/{id}/videos/playlist', params=param)

    def transmissions_items(self):
        epg = self.make_request('get', '/api/products/sections/rozklad-jazdy')

        if epg:
            id_a = epg[0]['elements'][0]['item']['id']
            id_b = epg[0]['elements'][1]['item']['id']

            now = calendar.now()
            since = datetime.datetime.strftime(now, '%Y-%m-%d') + 'T00:00+0200'
            till = datetime.datetime.strftime(now, '%Y-%m-%d') + 'T23:59+0200'
            param_tod = {
                'lang': 'pl',
                'platform': 'ANDROID',
                'since': since,
                'till': till
            }

            tomorrow = now + datetime.timedelta(days=1)
            since_tomorrow = datetime.datetime.strftime(tomorrow, '%Y-%m-%d') + 'T00:00+0200'
            till_tomorrow = datetime.datetime.strftime(tomorrow, '%Y-%m-%d') + 'T23:59+0200'

            param_tom = {
                'lang': 'pl',
                'platform': 'ANDROID',
                'since': since_tomorrow,
                'till': till_tomorrow
            }

            with self.concurrent() as con:
                con.a.today.jget(f'/api/products/lives/programmes?liveId[]={id_a}&liveId[]={id_b}', params=param_tod)
                con.a.tomorrow.jget(f'/api/products/lives/programmes?liveId[]={id_a}&liveId[]={id_b}', params=param_tom)

            return con.a

    def favourites(self):
        self.headers.update({
            'api-authentication': str(self.storage.get('user_data')['token']),
            'api-profileuid': str(self.storage.get('user_data')['profile_id'])
        })
        param = {'type': 'FAVOURITE'}
        return self.make_request('get', '/api/subscribers/bookmarks', params=param, headers=self.headers)

    def add_fav(self, f_id):
        self.headers.update({
            'api-authentication': str(self.storage.get('user_data')['token']),
            'api-profileuid': str(self.storage.get('user_data')['profile_id'])
        })
        param = {'type': 'FAVOURITE'}
        json = {
            "itemId": f_id
        }
        req = self.make_request('post', '/api/subscribers/bookmarks', params=param, payload=json, headers=self.headers)
        if req.status_code == 204:
            return True
        else:
            return False

    def remove_fav(self, f_id):
        self.headers.update({
            'api-authentication': str(self.storage.get('user_data')['token']),
            'api-profileuid': str(self.storage.get('user_data')['profile_id'])
        })
        params = {'type': 'FAVOURITE', "itemId[]": f_id}
        req = self.make_request('delete', '/api/subscribers/bookmarks', params=params, headers=self.headers)
        if req.status_code == 204:
            return True
        else:
            return False

    def search(self, query):
        params = {
            'lang': 'pl',
            'platform': 'ANDROID',
            'keyword': query
        }
        with self.concurrent() as con:
            con.a.vod.jget('/api/products/vods/search/VOD', params=params)
            con.a.serial.jget('/api/products/vods/search/SERIAL', params=params)
            con.a.episode.jget('/api/products/vods/search/EPISODE', params=params)
        return con.a


class Main(Plugin):
    """K-Sportowy plugin."""

    MENU = Menu(view='addons', items=[
        Menu(title='[B]Biblioteka[/B]', call='catalog'),
        Menu(title='[B]Rozkład jazdy[/B]', call='transmissions'),
        Menu(title='[B]Moja lista[/B]', call='favourites'),
        Menu(title='[B]Szukaj[/B]', call='searching')
        # Menu(title='[I]Ustawienia[/I]', call='noop'),
    ])

    searching = subobject()

    def __init__(self):
        super().__init__()
        self.kssite = KSSite()
        self.searching = Search(addon=self, site=self.kssite, method=self.searching_folder)

    def home(self):
        self.menu()
        self.kssite.init()

    def noop(self):
        pass

    def fmt(self, text, fmt=None):
        STYLE = {
            'folder_def': ['B'],
            'trans.time': {
                None: 'B;COLOR gray;[]'.split(';'),
                'live': 'B;COLOR green;[]'.split(';'),
                'current': 'B;COLOR orange;'.split(';'),
                'future': 'COLOR yellow;'.split(';'),
            },
            'folder_list_separator': ['COLOR khaki', 'B', 'I']
        }

        if fmt == 'folder':
            return stylize(text, STYLE['folder_def'])
        if fmt == 'separator':
            return stylize(text, STYLE['folder_list_separator'])
        if fmt == 'live':
            return stylize(text, STYLE['trans.time']['live'])
        if fmt == 'current':
            return stylize(text, STYLE['trans.time']['current'])
        if fmt == 'future':
            return stylize(text, STYLE['trans.time']['future'])
        if not fmt:
            return stylize(text, STYLE['trans.time'][None])

    def infolabel(self, item):
        if type(item) == dict:
            if item.get('item'):
                return {
                    'title': item['item'].get('title'),
                    'plot': item['item'].get('lead'),
                    'duration': item['item'].get('duration')
                }
            else:
                return {
                    'title': item.get('title'),
                    'plot': item.get('lead'),
                    'duration': item.get('duration')
                }

    def gen_art(self, item):
        def get_url(res):
            try:
                return images[res][0]['url']
            except (KeyError, IndexError):
                return None

        if item.get('item'):
            images = item['item']['images']
        else:
            images = item['images']
        return {
            'fanart': get_url('16x9'),
            'poster': get_url('1x1'),
        }

    def catalog(self):
        data = self.kssite.catalog()

        with self.directory() as kdir:
            for item in data:
                if 'Nadchodzące transmisje' in item['title']:
                    kdir.menu(self.fmt(item['title'], 'folder'), call(self.transmissions))
                    continue
                kdir.menu(self.fmt(item['title'], 'folder'), call(self.categories, item['id']))

    def categories(self, id):
        data = self.kssite.section(id)

        with self.directory() as kdir:
            for item in data.get('elements'):
                info = self.infolabel(item)
                art = self.gen_art(item)
                if item['item']['type'] == 'BANNER':
                    id = item['item']['webUrl'].split(',')[1]
                    kdir.menu(self.fmt(item['item']['title'], 'folder'), call(self.listing, id), info=info, art=art)
                if item['item']['type'] == 'EPISODE':
                    kdir.play(item['item']['title'], call(self.play_item, item['item']['id'], 'MOVIE'), info=info,
                              art=art, menu=[['Dodaj do mojej listy', call(self.add_fav, item['item']['id'])]])
                if item['item']['type'] == 'SERIAL':
                    kdir.menu(self.fmt(item['item']['title'], 'folder'), call(self.serial, item['item']['id']),
                              info=info, art=art)

    def serial(self, id):
        data = self.kssite.serial_section(id)

        with self.directory() as kdir:
            for item in data:
                kdir.menu(self.fmt(item['title'], 'folder'), call(self.serial_episode, id, item['id']))

    def serial_episode(self, id, e_id):
        data = self.kssite.serial_episode(id, e_id)

        with self.directory() as kdir:
            for item in data:
                info = self.infolabel(item)
                art = self.gen_art(item)
                kdir.play(item['title'], call(self.play_item, item['id'], 'MOVIE'), info=info, art=art,
                          menu=[['Dodaj do mojej listy', call(self.add_fav, item['id'])]])

    def listing(self, id):
        data = self.kssite.section(id)

        with self.directory() as kdir:
            for item in data.get('elements'):
                info = self.infolabel(item)
                art = self.gen_art(item)
                kdir.play(item['item']['title'], call(self.play_item, item['item']['id'], 'MOVIE'), info=info, art=art,
                          menu=[['Dodaj do mojej listy', call(self.add_fav, item['item']['id'])]])

    def transmissions_data(self):
        data = self.kssite.transmissions_items()

        live = []
        future = []
        tomorrow = []

        for item in data.today:
            now = datetime.datetime.now().timestamp()
            since = calendar.str2datetime(item['since'].replace('+02:00', '')).timestamp()
            till = calendar.str2datetime(item['till'].replace('+02:00', '')).timestamp()
            if since < now < till:
                live.append(item)
            if now < since:
                future.append(item)

        for item in data.tomorrow:
            tomorrow.append(item)

        tomorrow = [elem for elem in future if elem not in future]

        return {
            'live': live,
            'future': future,
            'tomorrow': tomorrow
        }

    def transmissions(self):
        data = self.transmissions_data()
        live = data['live']
        future = data['future']
        tomorrow = data['tomorrow']

        with self.directory() as kdir:
            if len(live) > 0:
                kdir.item(self.fmt('LIVE!', 'live'), call(self.noop))
                live = sorted(live, key=lambda i: i['since'])
                for l in live:
                    start = calendar.str2datetime(l['since'].replace('+02:00', ''))
                    start = f'{start:%H:%M}'
                    title = f'{self.fmt(start)} - {self.fmt(l["title"], "current")}'
                    info = self.infolabel(l)
                    art = self.gen_art(l)
                    kdir.play(title, call(self.play_item, l['live']['id'], 'LIVE'), info=info, art=art)
            if len(future) > 0:
                kdir.item(self.fmt('DZISIAJ!', 'separator'), call(self.noop))
                future = sorted(future, key=lambda i: i['since'])
                for f in future:
                    start = calendar.str2datetime(f['since'].replace('+02:00', ''))
                    start = f'{start:%H:%M}'
                    title = f'{self.fmt(start)} - {self.fmt(f["title"], "future")}'
                    info = self.infolabel(f)
                    art = self.gen_art(f)
                    kdir.item(title, call(self.noop), info=info, art=art)
            if len(tomorrow) > 0:
                kdir.item(self.fmt('JUTRO!', 'separator'), call(self.noop))
                tomorrow = sorted(tomorrow, key=lambda i: i['since'])
                for t in tomorrow:
                    start = calendar.str2datetime(t['since'].replace('+02:00', ''))
                    start = f'{start:%H:%M}'
                    title = f'{self.fmt(start)} - {self.fmt(t["title"], "future")}'
                    info = self.infolabel(t)
                    art = self.gen_art(t)
                    kdir.item(title, call(self.noop), info=info, art=art)
            if len(live) < 1 > len(future):
                kdir.item(self.fmt('Pusto'), call(self.noop))

    def favourites(self):
        favourites = self.kssite.favourites().get('items')

        with self.directory() as kdir:
            for fav in favourites:
                info = self.infolabel(fav)
                art = self.gen_art(fav)
                kdir.play(fav['item']['title'], call(self.play_item, fav['item']['id'], 'MOVIE'), info=info, art=art,
                          menu=[['Usuń z mojej listy',
                                 self.cmd.Container.Update(call(self.remove_fav, fav['item']['id']))]])

    def add_fav(self, f_id):
        if self.kssite.add_fav(f_id):
            xbmcgui.Dialog().notification('K-Sportowy', 'Dodano do mojej listy')

    def remove_fav(self, f_id):
        if self.kssite.remove_fav(f_id):
            xbmcgui.Dialog().notification('K-Sportowy', 'Usunięto z mojej listy')

    @search.folder
    def searching_folder(self, query):
        if query:
            results = self.kssite.search(query)

            vod = results.vod
            serial = results.serial
            episode = results.episode

            with self.directory() as kdir:
                if len(vod['items']) > 0:
                    kdir.item(self.fmt('VOD!', 'separator'), call(self.noop))
                    for v in vod['items']:
                        info = self.infolabel(v)
                        art = self.gen_art(v)
                        kdir.play(v['title'], call(self.play_item, v['id'], 'MOVIE'), info=info, art=art)
                if len(serial['items']) > 0:
                    kdir.item(self.fmt('PROGRAMY!', 'separator'), call(self.noop))
                    for s in serial['items']:
                        info = self.infolabel(s)
                        art = self.gen_art(s)
                        kdir.menu(s['title'], call(self.serial, s['id']), info=info, art=art)
                if len(episode['items']) > 0:
                    kdir.item(self.fmt('ODCINKI!', 'separator'), call(self.noop))
                    for e in episode['items']:
                        info = self.infolabel(e)
                        art = self.gen_art(e)
                        kdir.play(e['title'], call(self.play_item, e['id'], 'MOVIE'), info=info, art=art)

    def play_item(self, id, v_type):
        data = self.kssite.playlist(id, v_type)

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
            listitem.setProperty('inputstream.adaptive.stream_selection_type', 'manual-osd')

            xbmcplugin.setResolvedUrl(self.handle, True, listitem=listitem)

    def change_credentials(self):
        self.user_data.delete('credentials')
        self.user_data.delete('user_data')
        email = xbmcgui.Dialog().input('Podaj swój email', type=xbmcgui.INPUT_ALPHANUM)
        password = xbmcgui.Dialog().input('Podaj swoje hasło', type=xbmcgui.INPUT_ALPHANUM,
                                          option=xbmcgui.ALPHANUM_HIDE_INPUT)
        self.user_data.set('credentials', {
            'email': email,
            'pass': password
        })


# DEBUG ONLY
import sys  # noqa

log(f'K-Sportowy: {sys.argv}')

# Create and run plugin.
Main().run()
