from flask import Flask, request, jsonify
from requests.models import Response
from config import make_gpt_req, link_rule_to_asciidoc, portNo
from greenRules import getCategories, refreshCatalogue, ruleHelp, getAsciiDoc
from json import loads
import traceback
import logging
import sys

# ---------------------- Logging Configuration ----------------------
# Use Gunicorn logger if available, fallback to stdout
if "gunicorn" in sys.modules:
    logger = logging.getLogger("gunicorn.error")
else:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

# ---------------------- Flask App ----------------------
app = Flask(__name__)

# Redirect Flask's internal logger to use the same handlers
app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)

# ---------------------- Utility Functions ----------------------
def makeReq(category, rules, code):
    # Move join out of f-string to avoid backslash in expression
    rules_text = "- " + "\n- ".join(rules)
    return f"""These are the rules you should take note of for category {category}:
{rules_text}
Assess the following snippet of code against the list of rules above and give your response as a markdown, with each category as h1 and a summary of rules violated as an informative paragraph for the programmer to fix. Avoid any mention of inapplicable rules (keep only actionable feedback). Offer corrected code snippets to be replaced if remedy is complex to follow:
{code}
"""

def cleanupResponse(response):
    req_text = f"""Below is some feedback gathered for a programmer regarding code efficiency. Remove unrelated rules and feedback (keep only actionable feedback). Then, going by each category, group feedback to make it clear and actionable.
----start of feedback-----
{response}
-----end of feedback-----
Provide your summary in markdown format, organised for each category (h1) preserved."""
    clean_prompt = {
        "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
        "prompt": req_text,
        "max_tokens": 2500,
        "temperature": 0.7
    }
    return make_gpt_req(clean_prompt)

# ---------------------- Routes ----------------------
@app.route("/", methods=["GET"])
def startEndpoint():
    logger.info("startEndpoint called")
    return "Green Code API is running!"

@app.route("/getRules/<group>", methods=["GET"])
def getRules(group):
    logger.info(f"getRules called for group: {group}")
    categories = getCategories()
    if group == "all":
        return jsonify(categories)
    elif group in categories:
        return jsonify(categories[group])
    else:
        err = {
            "status_code": 404,
            "message": f"Category of rules called {group} not found",
            "details": "You can use GET /getRules/all to see all rules."
        }
        return jsonify(err), 404

@app.route("/refreshRules", methods=["GET"])
def refreshRules():
    logger.info("refreshRules called")
    try:
        data = loads(refreshCatalogue())
        return jsonify({"status_code": 200, "data": data})
    except Exception as e:
        logger.exception("Exception occurred while refreshing rules")
        return jsonify({
            "status_code": 500,
            "message": f"Encountered error while refreshing catalogue. Please retry: {e}"
        }), 500

@app.route("/checkCode", methods=["POST"])
def checkCode():
    snippet = request.json.get("code") if request.is_json else None
    if not snippet:
        logger.warning("checkCode called with empty snippet")
        response = Response()
        response.status_code = 400
        response._content = '{"error": "Bad request: No code snippet provided"}'
        return response

    feedback = ""
    try:
        categories = getCategories()
        for key, val in categories.items():
            req_text = f"Category: {key}\n{makeReq(key, val, snippet)}"
            request_obj = {
                "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
                "prompt": req_text,
                "max_tokens": 1500,
                "temperature": 0.7
            }
            feedback += make_gpt_req(request_obj).lstrip(" ```").lstrip("markdown\n").rstrip(" ```")
            logger.info(f"Queried GPT for category {key}")

        return ruleHelp(feedback) if link_rule_to_asciidoc else feedback

    except Exception as e:
        logger.exception("Error calling GPT API")
        return jsonify({
            "status": 500,
            "error": f"Error calling GPT API: {str(e)}"
        }), 500

@app.route("/ruleHelp/<ruleNo>", methods=["GET"])
def displayAsciiDoc(ruleNo):
    logger.info(f"displayAsciiDoc called for rule: {ruleNo}")
    return getAsciiDoc(ruleNo)

# ---------------------- Run Flask directly ----------------------
if __name__ == "__main__":
    logger.info("Starting Green Code Flask app directly (not via Gunicorn)")
    app.run(
        host="0.0.0.0",
        port=portNo,
        debug=False,
        use_reloader=False,
        threaded=False
    )
