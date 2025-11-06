import http.client
import json
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

conn = http.client.HTTPSConnection("api.notion.com")
payload = json.dumps({
   "callout": {
      "rich_text": [
         {
            "type": "text",
            "text": {
               "content": "前面文本\n"
            },
            "annotations": {
               "bold": True
            }
         },
         {
            "type": "mention",
            "mention": {
               "type": "page",
               "page": {
                  "id": "2a319740-7c23-8004-b792-f09b1c282df0"
               }
            }
         },
         {
            "type": "text",
            "text": {
               "content": "\n后面文本"
            }
         }
      ]
   }
})

with open('notion_config.json', 'r') as f:
    config = json.load(f)
os.environ['BLOCK_ID'] = config['blocks']

blocks_url = f"/v1/blocks/{os.getenv('BLOCK_ID')}"

headers = {
   'Authorization': os.getenv("NOTION_API_KEY"),
   'Notion-Version': os.getenv("Notion-Version"),
   'Content-Type': 'application/json',
   'Accept': '*/*',
   'Host': 'api.notion.com',
   'Connection': 'keep-alive'
}
conn.request("PATCH", blocks_url, payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))