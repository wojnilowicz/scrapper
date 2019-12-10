import json

json_to_selenium_keys = {
# 'Host raw':'domain',
'Name raw':'name',
'Content raw':'value',
'Path raw':'path',
'HTTP only raw':'httpOnly',
'Send for raw':'secure',
'Expires raw': 'expiry'
}

json_decode = {
"true": True,
"false": False,
"Any type of connection": False,
"Encrypted connections only": True,
}

json_numeric = [
'Expires raw'
]

def cookies_from_json(json_file_name):
    cookies = []
    with open(json_file_name, 'r') as json_file:
        json_file_contents = json.load(json_file)

    for json_cookie in json_file_contents:
        selenium_cookie = {}
        for json_key, selenium_key in json_to_selenium_keys.items():
            if json_key in json_numeric:
                selenium_cookie[selenium_key] = int(json_cookie[json_key])
            elif json_cookie[json_key] in json_decode:
                selenium_cookie[selenium_key] = json_decode[json_cookie[json_key]]
            else:
                selenium_cookie[selenium_key] = json_cookie[json_key]
        cookies.append(selenium_cookie)
    return cookies