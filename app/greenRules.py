
import os
import requests
from config import cat_json_file_path, gh_creedengo_rules_url, make_gpt_req, rule_commit_api, hash_json_path, refresh_frequency_days, ascii_doc_path, local_asciidocs, asciiDoc3_conf
from json import loads, dumps
import re
import datetime
from flask import url_for, Response
import asciidoc3.asciidoc3 as ad3

categories_headers = '["Code organization and style", "Declaration", "Expression and statements", "Others"]'

# ---------------------- AsciiDoc3 is typically ran as a CLI, standalone app.
#   I don't want to add another app with a bunch of bloat for functions we won't use, so here's an attempt to directly use it as a py library
#   Do note that this is not a documented behavior. we are reading from their GitHub and importing the required functions only to save time, space and handle error more visibly. 
#   AsciiDoc3 is written fully in Python, so I chose this to minimise stack size. The downside is that it requires knowledge of the installation path, and will throw "TypeError: expected str, bytes or os.PathLike object, not NoneType" if ran without the configs below.

# This gives the full path to the asciidoc3.py file
APP_DIR = os.path.dirname(os.path.abspath(ad3.__file__))
ad3.APP_DIR = APP_DIR

# asciidoc3_path = os.path.abspath(asciidoc3.__file__)
# asciidoc3_path = os.path.abspath(asciidoc3.__file__)
# # APP_DIR should be the directory containing asciidoc3.conf, which lives alongside asciidoc3.py
# APP_DIR = os.path.dirname(asciidoc3_path)
# asciidoc3.APP_DIR = APP_DIR
# ----------------------

def clean_output(json_gpt):
    print("Type of json_gpt:", type(json_gpt))
    print("Content of json_gpt:", json_gpt)
    return '{'+json_gpt.strip().split('{')[1].split('}')[0]+'}'

def retrieve_format_rules():
    try:
        rules_md = requests.get(gh_creedengo_rules_url)
        # -------------NOTE: using GPT to retrieve this will result in hallucination. Can't avoid with temperature.
        # - Parse using string logic based on markdown file structure instead.
        # formatted_rules_prompt=  f'The below is a markdown document on green code rules for you to extract. Read only the contents in the first table under section "Rules support matrix by techno" for columns Rule Key, Name and Description columns. Format them as a list, with rule key concatenated with the name and description. Ignore anything beyond the table ----start of rules-----{rules_md.text}'
        # rules_req_body = {"model": "Qwen/Qwen2.5-Coder-14B-Instruct",
        #     "prompt": formatted_rules_prompt,
        #     "max_tokens": 2000,
        #     "temperature": 0.2
        #     }

        # formatted_rules = make_gpt_req(rules_req_body)
        formatted_rules = rules_md.text.split('Non applicable rule\n')[1].split('## Rules to be reworked / measured / clarified')[0]
        summarise_rules_prompt= f'Extract and summarise all the rules below as guidelines that code should follow. Ensure that the phrasing is affirmative (e.g. "Use global variables" --> "Avoid using global variables to avoid unnecessary interpreter checks".) Ensure also that summaries are more clear and applicable than the rule by itself. e.g. "- CRJVM205 Use FetchType LAZY for collections on JPA entities to avoid loading unnecessary resources" <-- this is one rule. Summarise each rule and include the rule number: -----start of rules-----{formatted_rules}'
        summary_req_body={
            "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
            "prompt": summarise_rules_prompt,
            "max_tokens": 2000,
            "temperature": 0.2
        }
        summarised_rules = make_gpt_req(summary_req_body)
        classify_prompt = f'I have some green software rules here: {summarised_rules}. These are some categories for the rules: {categories_headers}. Return me **a single** JSON object with the categories as keys and an array of text (rules) as the value. Do not modify the rules text nor leave out any rules. Include the rule numbers with the rule as a single string. Result should be one object readable by json.loads method in python.'
        classify_req_body = {
            "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
            "prompt": classify_prompt,
            "max_tokens": 4000,
            "temperature": 0.2
        }
        response = make_gpt_req(classify_req_body)
        return response
    except Exception as e:
        return {
            'status_code': 500,
            'error': e
        }
    
def refreshCatalogue():
    rules = retrieve_format_rules()
    cleaned = clean_output(rules)
    with open(cat_json_file_path, 'w') as f:
        f.write(cleaned)
    return cleaned

def getCategories():
    if not (os.path.isfile(cat_json_file_path) and os.path.exists(cat_json_file_path)):
        refreshCatalogue()
    with open(cat_json_file_path, 'r') as g:
        return loads(g.read())
    
def ruleHelp(feedback):
    # FEATURE FLAG: return self-hosted local link. Configure in app/config.py or comment out to disable.
        # Flag for local asciidoc switches the output to the local /ruleHelp/<ruleNo> endpoint for deployments without external network connection
    if(local_asciidocs):
        return  re.sub(r'\b(GCI\d{1,3}|CRJVM\d{1,3})\b', lambda match: localRuleUrl(match.group(0)), feedback)
    
    # With self-hosted local link disabled: 
    if not (os.path.isfile(hash_json_path) and os.path.exists(hash_json_path)):
        retrieve_hash()
    #################################################################
    #   (1) get the local saved commit hash of the rules repo.      #
    #   (2) check when hash was last updated                        #
    #       (2a) if it's old, update                                #
    #   (3) get hash and build link into the strings via re.sub     #
    #################################################################
    with open(hash_json_path, 'r') as f:
        default_hash_obj = loads(f.read()) # (1)
        refresh_exp_date = datetime.datetime.now() - datetime.timedelta(days=refresh_frequency_days) 
        # Note: Timezone is not relevant, so we can just use ISO8601 as string to compare dates directly
        if(default_hash_obj['commit_date']<refresh_exp_date.isoformat()): # (2a) Eeeee stinky, expire liao not fresh.
            print('Last update: {default_hash["commit_date"]}. Retrieving latest.')
            new_hash_obj = retrieve_hash()
            with open(hash_json_path, 'w') as f:
                print('Updating cache')
                new_hash_obj["commit_date"] = datetime.datetime.now().isoformat()
                f.write(dumps(new_hash_obj))
    with open(hash_json_path, 'r') as f:
        hash_obj = loads(f.read()) # (3)
        sha_hash = hash_obj["hash"]

    return re.sub(r'\b(GCI\d{1,3}|CRJVM\d{1,3})\b', lambda match: formatRuleUrl(match.group(0), sha_hash), feedback)

def formatRuleUrl(ruleNo, sha_hash):
    return f'[{ruleNo}](https://github.com/green-code-initiative/creedengo-rules-specifications/tree/{sha_hash}/src/main/rules/{ruleNo})'

def localRuleUrl(ruleNo):
    file_url = url_for('displayAsciiDoc', ruleNo=ruleNo, _external=True) # url_for is a Flask-specific function. Only use when there is an app running. Otherwise you'll get an error since the interpreter can't find any host name to work with
    return f'[{ruleNo}]({file_url})'

def retrieve_hash():
    hash_response = requests.get(rule_commit_api)
    hash_res = hash_response.json()
    print('-----------hash content-------------')
    print(hash_res)
    cache_obj = { "commit_date": hash_res['commit']['commit']['author']['date'], "hash": hash_res['commit']['sha'] }
    with open(hash_json_path, 'w') as f:
        f.write(dumps(cache_obj))
    return cache_obj

def is_github_hash(s):
    return bool(re.fullmatch(r'[a-f0-9]{40}', s))

############# This version only returns AsciiDoc. Honestly it's readable enough, just feel like we might as well use HTML5 if we're running a flask app already 
# def getAsciiDoc(ruleNo):
#     docName = ruleNo+'.asciidoc'
#     docPath = os.path.join(ascii_doc_path, docName)
#     with open(docPath, 'r') as f:
#         return f.read()

def getAsciiDoc(ruleNo):
    doc_name = ruleNo + '.asciidoc'
    doc_path = os.path.join(ascii_doc_path, doc_name)
    if not os.path.exists(doc_path):
        return "Rule not found", 404
    # Create HTML output path in memory or temp
    html_output = doc_path.replace('.asciidoc', '.html')
    try: 
        ad3.asciidoc3(backend='html5',doctype='article',confiles=[asciiDoc3_conf],infile=doc_path,outfile=html_output, options=['--skip'])
    
        with open(html_output, 'r', encoding='utf-8') as f:
            html = f.read()

        return Response(html, mimetype='text/html')
    except SystemExit as e:
        return f"Error parsing asciidoc as html: {e}"

if __name__ == '__main__':
    # print(getCategories())
    print(ruleHelp(' ```markdown\n             ## GCI11: Limit multiple accesses to the same DOM element to enhance performance.\n             The provided code does not interact with the DOM, so this rule does not apply.\n\n             ## GCI12: Batch multiple style changes to reduce computational overhead.\n             The provided code does not involve any style changes, so this rule does not apply.\n\n             ## GCI13: Prefer API collections with pagination for efficient data handling.\n             The provided code processes a list of data URLs without considering pagination, which could lead to inefficiencies if the datasets are large. To address this, consider using APIs that support pagination.\n\n             ## GCI5: Use `preparedStatement` instead of `Statement` to optimize SQL queries.\n             The provided code does not involve SQL queries, so this rule does not apply.\n\n             ## GCI7: Rewrite native getters/setters to improve performance.\n             The provided code does not use native getters/setters, so this rule does not apply.\n\n             ## Summary\n             The primary issues in the provided code are related to inefficient data handling and lack of error handling. Specifically, making individual HTTP requests in a loop without considering pagination can lead to performance bottlenecks. Additionally, there is no error handling for network requests, which can cause the program to fail silently. To improve the code, consider implementing pagination for API requests and adding error handling for network operations.\n '))