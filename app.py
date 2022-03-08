from flask import Flask, render_template
from flask import request
import json
import pdb
import requests
import shelve
import atexit
import time
from benedict import benedict


app = Flask(__name__)

def unflatten(dictionary):
    resultDict = dict()
    for key, value in dictionary.items():
        parts = key.split(".")
        d = resultDict
        for part in parts[:-1]:
            if part not in d:
                d[part] = dict()
            d = d[part]
        d[parts[-1]] = value
    return resultDict

class Browser(object):
    def __init__(self, name, url, template, default={}, headers={}, xpath=[]):
        self.name = name
        self.url = url
        self.headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01', 
                'content-type': 'application/json; charset=UTF-8', 
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36', 
                'accept-language': 'zh-CN,zh;q=0.9'}
        self.headers.update(headers)
        self.cache = shelve.open(name)
        self.template = template
        self.default = default.copy()
        self.payload = {}

    def query(self, **kwargs):
        self.payload = benedict(self.default.copy())
        for k, v in kwargs.items():
            self.payload[k] = v
        print(self.payload)
        request_key = "_".join(map(str, self.payload.values()))
        if request_key in self.cache:
            resp = self.cache[request_key]
        else:
            r = requests.post(self.url, data=json.dumps(self.payload), headers=self.headers)
            resp = r.json()
            self.cache[request_key] = resp.copy()
        return resp

    def render(self, **kwargs):
        resp = self.query(**kwargs)
        debug_json = dict([(k, v) for k, v in resp.items() if k != 'list' and v is not None and v != []])
        return render_template(self.template, raw_json = json.dumps(debug_json, indent=4, ensure_ascii=False), payload=self.payload, **resp)

    def close_cache(self):
        print("Closing cache")
        self.cache.close()

services = {
    'rc': Browser('reverso', "https://context.reverso.net/bst-query-service", "reverso_context.html", {'source_lang': 'en', 'target_lang': 'zh', 'source_text': '', 'target_text': '', 'mode': '1', 'nrows': '50'}),
    'deepl': Browser('deepl', "https://www2.deepl.com/jsonrpc", "deepl.html",
        {"jsonrpc":"2.0","method": "LMT_handle_jobs","params":{"jobs":[{"kind":"default","sentences":[{"text":"Tell me the story","id":0,"prefix":""}],"raw_en_context_before":[],"raw_en_context_after":[],"preferred_num_beams":4,"quality":"fast"}],"lang":{"user_preferred_langs":["ZH","EN"],"source_lang_user_selected":"auto","target_lang":"ZH"},"priority":-1,"commonJobParams":{"browserType":129,"formality":None},"apps":{"usage":5},"timestamp":1646624556415},"id":48930046}
        )
}

@app.route('/favicon.ico')
def favicon():
    return ''

@app.route('/<service>/')
@app.route('/<service>')
@app.route('/')
def index(service=None):
    if service is None:
        responses = {}
        responses['DeepL'] = services['deepl'].render(**{'params.jobs[0].sentences[0].text': request.args['query']})
        responses['Reverso Context'] = services['rc'].render(**{'source_text': request.args['query'], 'nrows': 5})
        return render_template('index.html', responses=responses)
    else:
    	return services[service].render(**request.args)


if __name__ == '__main__':
      app.run(host='0.0.0.0', port=5678, debug=True)
