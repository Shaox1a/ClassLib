"""Read-only smoke check against one HTTPS deployment, without following redirects."""
import argparse
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='Exact deployment URL from the Vercel dashboard')
    target = urlsplit(parser.parse_args().url)
    if (target.scheme != 'https' or not target.hostname or target.username is not None
            or target.password is not None or target.path not in ('', '/') or target.query or target.fragment):
        parser.error('Expected an HTTPS origin')

    opener = build_opener(NoRedirect)
    for path, marker in [('/', None), ('/login/', b'csrfmiddlewaretoken'),
                         ('/static/css/site.css', b'{'), ('/static/js/login.js', b'addEventListener')]:
        try:
            response = opener.open(f'https://{target.netloc}{path}', timeout=30)
        except HTTPError as error:
            response = error
        except (TimeoutError, URLError) as error:
            raise SystemExit(f'Could not reach {target.hostname}: {error}') from None
        with response:
            if marker is None:
                location = urlsplit(response.headers.get('Location', ''))
                ok = (response.status == 302 and not location.netloc and location.path == '/login/')
            else:
                ok = response.status == 200 and marker in response.read()
            if not ok:
                raise SystemExit(f'{path} failed (HTTP {response.status}). Check deployment access and logs.')
            print(f'OK {path}')


if __name__ == '__main__':
    main()
