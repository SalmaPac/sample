import sys
import re
from pathlib import Path

'''
This file is here to clean up highlight rules for local rendering. This is invoked for maintenance script pull_local_asciidocs.bat or .sh

Issue: Highlight package is used by python's asciidoc3 to render asciidoc into html5. However, not all code formats are supported.
In particular, typescript can't be read, and the code will fail to render completely. 

Solution: This script here helps to check through the directory to replace all [source,typescript] with [source,javascript] so that the code examples can be seen
'''

def fix_typescript_syntax(adoc_path: Path):
    content = adoc_path.read_text(encoding='utf-8')

    # Regex to match '[source,typescript' followed by optional chars until ']'
    fixed_content = re.sub(r'(\[source,)typescript(\b[^]]*)', r'\1ts\2', content)

    if fixed_content != content:
        adoc_path.write_text(fixed_content, encoding='utf-8')
        print(f"Fixed TypeScript syntax highlighting in {adoc_path}")
    else:
        print(f"No changes needed in {adoc_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_asciidoc_ts.py <file1.adoc> [file2.adoc ...]")
        sys.exit(1)

    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if path.is_file():
            fix_typescript_syntax(path)
        else:
            print(f"File not found: {filepath}")
