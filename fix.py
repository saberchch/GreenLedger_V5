with open("templates/pages/dashboard/messages/chat.html", "r") as f:
    text = f.read()
import re
text = re.sub(r'const ME_ID = \{\{ current_user_id \}\n\s*\}\;\n\s*const ME_NAME = \{\{ current_user_name \| tojson \}\}\;', 'const ME_ID = {{ current_user_id }};\n        const ME_NAME = {{ current_user_name | tojson }};', text)
text = re.sub(r'const ME_ID = \{\{ current_user_id \}\n\s*const ME_NAME = \{\{ current_user_name \| tojson \}\}\;', 'const ME_ID = {{ current_user_id }};\n        const ME_NAME = {{ current_user_name | tojson }};', text)
text = re.sub(r'const ME_ID = \{\{ current_user_id \}\;\n\s*const ME_NAME = \{\{ current_user_name \| tojson \}\}\;', 'const ME_ID = {{ current_user_id }};\n        const ME_NAME = {{ current_user_name | tojson }};', text)
with open("templates/pages/dashboard/messages/chat.html", "w") as f:
    f.write(text)
