from lxml import html
import requests
import re
from IPython.display import display, HTML, JSON
import json
import urllib.request
from datetime import date

class DuplicateEntry(Exception):
    pass

class EntryNotFound(Exception):
    pass

class MultipleEntries(Exception):
    pass

class AnkiDuplicate(Exception):
     def __init__(self, message):
        self.message = message
        super().__init__(self.message)

# anki connect
def request_anki(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invoke_anki(action, **params):
    requestJson = json.dumps(request_anki(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        if (response['error'] == 'cannot create note because it is a duplicate'):
            raise DuplicateEntry(response['error'])
        raise Exception(response['error'])
    return response['result']

def add_note(trs:dict, deck:str='Euskara::z - incoming', tags=['elhuyar_import_v0',]): 
    params = {
        "note": {
            "deckName": deck,
            "modelName": "Basic (and reversed card)",
            "fields": {
                "Front": trs['word'],
                "Back": trs['translation']
            },
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": "Euskara",
                    "checkChildren": True,
                    "checkAllModels": False
                }
            },
            "tags": tags,
        }
    }
    return invoke_anki(action='addNote', **params)

def get_translation(word):
    
    response = requests.get(f"https://hiztegiak.elhuyar.eus/eu_fr/{word}")
    tree = html.fromstring(response.content)

    results = tree.xpath('//div[contains(@class, "emaitza-lerroa")]/h1')

    if (len(results)==0):
        raise EntryNotFound(f"Translation not found for {word}")

    if (len(results)>1):
        raise MultipleEntries(f"Words with multiple definition are not supported ({word})")


    result_html = tree.xpath('//div[contains(@class, "emaitza-lerroa")]/h1')[0].text_content()

    trs_blocks = tree.xpath(f'//div[contains(@class, "emaitza-lerroa")][1]/following::ul[contains(@class, "hizkuntzaren_arabera")][1]//p[contains(@class, "lehena")]')
    trs_html = '<br>'.join([re.sub(r'\s+', ' ', tr.text_content()).strip() for tr in trs_blocks])

    trs_result = {'word': result_html, 'translation': trs_html}

    return trs_result

def main():

    with open('new_words.txt', 'r') as fichier:
        # Lire le contenu du fichier
        file_content = fichier.read()

    words = file_content.split('\n')
    words = [ word.strip() for word in words if word.strip()]

    results = {}
    for word in words:
        while (word):
            try:
                res = add_note(get_translation(word))
                results[word] =  {'status': 'done', 'translation': res}
            except EntryNotFound as e:
                word = input(f'\n{word} not found, correct or leave blank to skip word: ')
            except DuplicateEntry as e:
                results[word] =  {'status': 'duplicate'}
                break
            except (MultipleEntries, Exception) as e:
                results[word] =  {'status': 'failed', 'cause': str(e)}
                break
            finally:
                print('.', end='')

    errors = {key: value for key, value in results.items() if value.get("status") != "done"}
    print(f"{len(errors)} errors on {len(results)} results for {len(words)} words : ")
    if (len(errors) > 1): 
        print(json.dumps(errors, indent=4)) 


if __name__ == '__main__':
    main()
