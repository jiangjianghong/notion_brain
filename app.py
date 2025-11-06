import http.client
import json
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


# 修改 notion_config.json 中的 block id
def change_block_id(block_id: str):
   with open('notion_config.json', 'r') as f:
      config = json.load(f)
   config['target_block'] = block_id
   with open('notion_config.json', 'w') as f:
      json.dump(config, f, indent=4)


# 修改 Notion 中的指定 block 内容
def change_block(rich_text:list):
   with open('notion_config.json', 'r') as f:
      config = json.load(f)
   os.environ['BLOCK_ID'] = config['target_block']
   blocks_url = f"/v1/blocks/{os.getenv('BLOCK_ID')}"
   conn = http.client.HTTPSConnection("api.notion.com")
   payload = json.dumps({
      "callout": {
         "rich_text": rich_text
      }
   })
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
   data = res.read().decode("utf-8")
   print(data)

# 查询 页面内容
def get_page_content(page_id: str):
   page_url = f"/v1/blocks/{page_id}/children?page_size=100"
   conn = http.client.HTTPSConnection("api.notion.com")
   payload = json.dumps({})
   headers = {
      'Authorization': os.getenv("NOTION_API_KEY"),
      'Notion-Version': os.getenv("Notion-Version"),
      'Content-Type': 'application/json',
      'Accept': '*/*',
      'Host': 'api.notion.com',
      'Connection': 'keep-alive'
   } 
   conn.request("GET", page_url, payload, headers)
   res = conn.getresponse()
   data = json.loads(res.read().decode("utf-8"))
   return data


# 获取最近修改的页面 ID
def get_lasted_change_page_id(page_size):
   
   with open('notion_config.json', 'r') as f:
      config = json.load(f)
   target_page = config['target_page']

   conn = http.client.HTTPSConnection("api.notion.com")
   payload = json.dumps({
      "sort": {
         "timestamp": "last_edited_time",
         "direction": "descending"
      },
      "page_size": page_size+1
   })
   headers = {
      'Authorization': os.getenv("NOTION_API_KEY"),
      'Notion-Version': os.getenv("Notion-Version"),
      'Content-Type': 'application/json',
      'Accept': '*/*',
      'Host': 'api.notion.com',
      'Connection': 'keep-alive'
   }
   conn.request("POST", "/v1/search", payload, headers)
   res = conn.getresponse()
   data = json.loads(res.read().decode("utf-8"))
   results = data.get("results", [])

   ## 过滤自己
   final_data=[]
   for i in results:
      if i.get("id")!=target_page:
         final_data.append(i.get("id"))
   if len(final_data)>page_size:
      final_data=final_data[:page_size]
   return final_data

# 页面提及url 包装
def wrap_url(id: str):
   return {
               "type": "mention",
               "mention": {
                  "type": "page",
                  "page": {
                     "id": id
                  }
               }
            }

# text 包装
def wrap_text(text: str,bold: bool =False):
   return {
               "type": "text",
               "text": {
                  "content": text
               },
               "annotations": {
                  "bold": bold
               }
            }

# 关键词搜索
def search_pages(keyword: str = "", obj_type: str = "page", limit: int = 10):
    conn = http.client.HTTPSConnection("api.notion.com")
    payload = json.dumps({
        "query": keyword,
        "object": obj_type,
        "sort": {"timestamp": "last_edited_time", "direction": "descending"},
        "page_size": limit
    })
    headers = {
        "Authorization": os.getenv("NOTION_API_KEY"),
        "Notion-Version": os.getenv("Notion-Version", "2022-06-28"),
        "Content-Type": "application/json"
    }
    conn.request("POST", "/v1/search", payload, headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode())
    results = []
    for item in data.get("results", []):
        title = ""
        if item["object"] == "page":
            title = item["properties"].get("Name", {}).get("title", [{}])[0].get("plain_text", "")
        elif item["object"] == "database":
            title = item["title"][0]["plain_text"] if item["title"] else ""
        results.append({
            "id": item["id"],
            "title": title,
            "type": item["object"],
            "last_edited_time": item["last_edited_time"]
        })
    return results
 
# 拉取页面属性

def get_page_properties(page_id: str):
    conn = http.client.HTTPSConnection("api.notion.com")
    headers = {
        "Authorization": os.getenv("NOTION_API_KEY"),
        "Notion-Version": os.getenv("Notion-Version", "2022-06-28")
    }
    conn.request("GET", f"/v1/pages/{page_id}", "", headers)
    res = conn.getresponse()
    return json.loads(res.read().decode())
 

# 拿页面/块100条正文内容

def get_blocks(block_id: str, recursive: bool = False):
    """recursive=True 时自动再抓子块"""
    conn = http.client.HTTPSConnection("api.notion.com")
    headers = {
        "Authorization": os.getenv("NOTION_API_KEY"),
        "Notion-Version": os.getenv("Notion-Version", "2022-06-28")
    }
    conn.request("GET", f"/v1/blocks/{block_id}/children?page_size=100", "", headers)
    res = conn.getresponse()
    blocks = json.loads(res.read().decode()).get("results", [])
    if recursive:
        for b in blocks:
            if b.get("has_children"):
                b["children"] = get_blocks(b["id"], recursive=True)
    return blocks
 


if __name__ == "__main__":

   url=get_lasted_change_page_id(10)
   print("获取到最近修改的页面 ID:")
   print(url)

   rich_text=[
      wrap_text("前面的文本哈哈哈\n", True),
      wrap_text("第一处修改", False),
      wrap_url(url[0]),
      wrap_text("\n第二处修改", False),
      wrap_url(url[1]),
      wrap_text("\n后面的文本", False)
   ]

   change_block(rich_text)




   # page_content=get_page_content("2a319740-7c23-8004-b792-f09b1c282df0")

   
