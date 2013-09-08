import requests


def generate_map():
    r = requests.get(
        "http://api.enforceapp.com/complaint/all"
    )
    data = r.json()

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    static_urls = ['/', '/news', '/top', '/terms', '/privacy', '/contact']
    url_base = 'http://enforceapp.com'
    for url in static_urls:
        xml += '<url>\n'
        xml += '<loc>' + url_base + url + '</loc>\n'
        xml += '</url>\n'

    for complaint in data:
        url = complaint["public_url"]
        xml += '<url>\n'
        xml += '<loc>' + url_base + url + '</loc>\n'
        xml += '</url>\n'

    xml += '</urlset>'

    return xml


def write_to_file():
    sitemap = generate_map()
    sitemap_file = open("sitemap.xml", "w")
    sitemap_file.write(sitemap)
    sitemap_file.close()

    return None

write_to_file()
