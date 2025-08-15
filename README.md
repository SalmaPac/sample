# 🌱 EcoCode for Sunshine.Coder

This is a standalone container that accepts http queries to interact with Sunshine.Coder's LLM internally.
# 🏃Running
To start the container, the easiest way is to
1. Navigate to the repository root
2. run `docker compose up`.

## 🐳 Running as a standalone container
If you want to run the container by itself, you can find the Dockerfile at `app/Dockerfile`
1. Run `cd app` at the repository root to enter the `/app` folder
2. Run `docker build .`. This creates the docker image
    3. You are recommended to tag your images in the format of `docker build -t *you_username*/greencode:*version_no* .` for maintainability
4. (Optional) Run `docker push *you_username*/greencode:*version_no*` to publish to your Dockerhub

## 🐙Running as part of your existing Docker Compose set up
1. Copy over the repo files
2. You may rename "app" directory to a more descriptive name. We will call this `yourAppRoot` below
3. Under `services` in your docker compose configuration, include this indented block:

```yaml
green_code:
    build:
      context: app
      target: runner

    ports:
      - '8000:8000'

    environment:
      - FLASK_RUN_PORT=8000
      - FLASK_RUN_HOST=0.0.0.0
      - gpt_ep=your_gpt_endpoint
```

4. Do remember to replace your `gpt_ep` variable with your LLM's completion endpoint
# 🖋️ Modifying

You can find app-wide variables in `app/config.py`. This includes
- the default gpt endpoint
- source file for the rules by Green Code Initiative as a GitHub raw
- path to a local copy of the categorised rules
## 📏 Updating ruleset

- You can use the end point `GET http://hostname:port_no/refreshRules` to trigger the update event
    - First, a call is made to retrieve the GitHub file for rules markdown from the public repo
        - This is a permalink, but the file structure may change
        - The assumption is that the LLM should be able to extract the necessary information regardless
        - However, string parsing to narrow the file down reduces hallucinations greatly, so should the file structure change such that the previous slicing logic no longer works, you are recommended to update the logic under `app/greeRules.py`. Search for the declaration for the `formatted_rules` variable
    - Next, the LLM is called to parse the markdown table in the rules document. It then returns the rule key, summarised and rephrased rules as a readable list. Rule key is retained for manual checks
    - Lastly, the LLM is called again to categorise the rules into 3 broad categories and 1 catch call
    - The categorised rule is then used to overwrite the file `app/categories.json` for the instance. Note that this new version is overwritten when the container restarts
### 🗄️ Updating rule categories
You can update the categories used by changing the `categories_headers` variable at the top of `app/greenRules.py`

### ✅ Verifying update
You can run the `GET http://hostname:port_no/getRules/all` endpoint to see the contents of `app/categories.json` to verify a rule refresh, or to retrieve the rules used.

If you only need a particular category, query using `GET http://hostname:port_no/getRules/{category_name}` instead
# 👨‍💻 Checking code snippets
1. Build your request as a JSON object with attribute `code`. e.g.
```json
  "code": "function processData(data) {
	    // This function processes a large dataset without any optimization
	
	    let results = [];
	    // Inefficient loop with nested operations
	
	    for (let i = 0; i < data.length; i++) {
		    // CPU-intensive operation inside loop
	
	        let transformed = complexTransformation(data[i]);
	        // Multiple DOM updates inside loop
	        document.getElementById('results').innerHTML += transformed;
	        // Unnecessary API call inside loop
	        fetch('https://api.example.com/process', {
	          method: 'POST',body: JSON.stringify({ item: transformed })
	        });
	        results.push(transformed);
	    }
	    return results;  
	}"
```
2. Ensure the container is running
3. Send a Post request with the contents in step 1 as the body to the endpoint `POST http://hostname:port_no/checkCode
# Examples
You can find a Postman collection at the repository root to find more example of uses, as well as possible error cases. Note that sometimes `refreshRules` may fail due to LLM quirks (returning nothing but whitespaces, etc.) so for `refreshRules` in particular, you may need to rerun the endpoint before confirming a programmatic bug.


----

# 🧪 Experimental features

You can set all feature flags within `app/config.py`

| Feature flag            | Feature details                                                                                                                                                                                                                                                                                                                                           |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `link_rule_to_asciidoc` | The feedback from `/checkCode` endpoint will now include a link to the rule's documentation. This doc will help provide a more detailed explanation to why the rule matters in the context of green software, and provide examples of violating code and corrected code                                                                                   |
| `local_asciidocs`       | Using a locally downloaded set of `.asciidocs`, this feature hosts the downloaded docs as html, and replaces the feedback links in link_rule_to_asciidoc8 with the container's hosted version of the docs. e.g. if your container is in 10.120.120.01:8000, you can check rule GCI13 at http://10.120.120.01:8000/ruleHelp/GCI13 as HTML in your browser. |

---
## 🔗 FEATURE link_rule_to_asciidoc: Add hyperlink to documentation with GitHub permalinks

Feature flag is set in `app/config.py` as boolean, true means the feature is on. You can unflag the feature in `app/greenCode.py` under function `checkCode()`

To ensure a more informative developer's experience, this feature hopes to add capabilities to hyperlink the asciidoc kept by the Creedengo team within the LLM's feedback so that users can click on links to refer to their documentation.

> The permalink includes languages as part of the path, making it not possible to directly access from the rule number alone. E.g. https://github.com/green-code-initiative/creedengo-rules-specifications/blob/a7eefd37bf3d08f6d63a9a7b25f6158a88a89db4/src/main/rules/GCI10/python/GCI10.asciidoc. As such, we will direct the user to the rule's root folder instead for their own navigation. (i.e. one folder level above the target asciidoc)


### 🔄 Caching the commit hash of Creedengo Rules repo

> NOTE: If you run the app as-is, the permalink will be updated automatically every 30 days by default. You can change the frequency of refresh (see next section on how to do so) and you do not have to explicitly refresh by yourself. This section is just for maintenance information.

To ensure successful but updated retrieval of the Creedengo rules from the specifications repository, a permalink is needed in which the commit hash is passed in as part of the permalink.

This system has a hash object stored within the `app/` folder as a JSON with the following structure:

```JSON
{
  "hash": "<string of the commit hash>",
  "commit_date": "<date of last commit as string>"
}
```

When fetching, the server first queries GitHub API to retrieve the Master branch commit details. This REST API uses HTTP GET, and the URL is set within `app/config.py` as variable `rule_commit_api`.

If it has been more than a month since the last retrieval, the cache will be updated. This serves 2 main purposes:

1. A fallback value is in effect in case the commit retrieval api fails
2. Minimise REST API HTTP usage rates

The most foreseeable point of failure is rate limit, capped at 60 requests/h for unauthorized HTTP requests. As such we do not retrieve the full content for the rule details (instead generating the link for self reference from users) and minimise calls whenever we can.

### 🔄 Setting hash cache refresh rate

The default frequency is set to 30 days. You can change this under `app/config.py`. The endpoint to retrieve the commit records are also under `app/config.py` as string named `rule_commit_api`.

Actual refresh gating logic resides within `app/greenRules.py` under function `format_rule_url`.

---
## 🏝️ FEATURE `local_asciidocs`: Host help documentation on local as HTML (for deployments without NAT Gateways or external internet capabilities)

When this feature is on, feedback markdown will link to the container that this solution is running in with `http://<hostname>/ruleHelp/<ruleNo>`.

This means that we are hosting a local copy of the relevant  `.asciidoc` documentation (examples of acceptable and unacceptable code, why it matters for green software etc provided by Creedengo project).

### Configurations

| Variable         | Meaning                                                                                                     | Location                                                                                                                                           |
| ---------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ascii_doc_path` | Location where the repo's cleaned .asciidoc are hosted within the container                                 | `app/config.py`, `app/pull_local_asciidocs.sh`, `app/pull_local_asciidocs.bat` (Note on the 2 batch scripts: OUTPUT_DIR should match the variable) |
| `asciiDoc3_conf` | Location of the asciidoc to html parser config. Actually not needed, but will make the solution less flimsy | `app/config.py`                                                                                                                                    |

#### 🐳 Updating local asciidocs using shellscript in docker exec

Run the following:
```bash
docker exec -it <container_name> bash -c "./app/pull_local_asciidocs.sh"
```

Replace `<container_name>` with the name or ID of your running Docker container (you can find it with `docker ps`).

✅ Example:

```bash
docker exec -it green_code bash -c "./app/pull_local_asciidocs.sh"
```

This will:
- Clone the latest rule specification repo.
- Clean and convert `typescript` blocks to `ts` (for syntax highlighting). (see app/cleaner.py help string for more information on why this is needed)
- Copy `.asciidoc` files into the local pattern library.
- Clean up temporary files, i.e. files from the repo that we don't need/ aren't documentation files
#### 📝 Note:
Ensure the container has git and python3 installed (should already be included if using the provided Dockerfile).

If you get permission errors, you may need to prefix with sudo or adjust file ownership inside the container.

### 🪟 Updating in Windows before launching in Docker
Make sure you are at the project root, if not, run `cd <Path to project root>` first. Then, run the following:
```bat
./app/pull_local_asciidocs.bat
```

Using Docker Desktop, ensure that you have removed the previous image and compose containers. Then, restart the container for the changes to take effect.

The steps of what happens are exactly the same as the Docker exec version described above.