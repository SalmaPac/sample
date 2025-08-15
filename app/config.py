from os import environ, path
from requests import post
from json import loads

portNo = 8000
# ------------- FEATURE FLAGS --------------------
link_rule_to_asciidoc = True # enables external link to asciidoc repository on GitHub
local_asciidocs = True # Hosts asciidoc at local endpoint, links the comments to this local version instead.
# ------------------------------------------------

# -------------- Constants -----------------------
gptEndpoint = environ.get('gpt_ep') or 'http://genaillm02.devnet.int:8081/v1/completions'
dir = path.dirname(__file__)

#   These refer to the cache for the categorised rules
#       Rules are retrieved from creedengo's rule specification repository as a GitHub raw bytearray/string
#       The retrieved rules are parsed in `app/greenRules.py`, where it will be edited, categorised, and written as a local file in the path defined in cat_json_file_path
#       URL to the GitHub raw is saved here to retrieved with the request library using HTTP GET
cat_json_file_path = path.join(dir,'categories.json')
hash_json_path = path.join(dir,'hash.json')
gh_creedengo_rules_url = 'https://raw.githubusercontent.com/green-code-initiative/creedengo-rules-specifications/refs/heads/main/RULES.md'
ascii_doc_path = path.join(dir,'pattern-library')
asciiDoc3_conf = path.join(dir,'asciidoc3.conf')
#   These refer to the variables to check the latest commit to the rules specification repository. 
#       The API is to fetch the hash number (for permalink to be enabled in GPT feedback) 
#       The refresh_frequency_days refer to the number of days since the last commit or check.
#   E.g. if you want to check for new commits every week instead of every month, change the frequency to 7 instead of 30
rule_commit_api = 'https://api.github.com/repos/green-code-initiative/creedengo-rules-specifications/branches/master'
refresh_frequency_days = 30
# ------------------------------------------------

# Shared utility functions 
def make_gpt_req(request_obj):
    response = post(gptEndpoint, json=request_obj)
    
    if response.ok:
        result = loads(response.text)
        print('-----------------GPT response-----------------')
        print(result, flush=True)
        print('----------------------------------------------')
        return result['choices'][0]['text']
    else:
        return {
            'status': response.status_code,
            'error': f'GPT API error: {response.text}'
        }