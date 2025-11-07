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

   # 调试：打印发送的 payload
   print("\n=== 发送到 Notion 的 Payload ===")
   print(f"Rich text 元素数量: {len(rich_text)}")
   print(f"Payload 前 500 字符: {payload[:500]}...")

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

   print("\n=== Notion API 响应 ===")
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
    
    # 构建请求 payload
    payload_dict = {
        "sort": {"timestamp": "last_edited_time", "direction": "descending"},
        "page_size": limit
    }
    
    # 只有当 keyword 不为空时才添加 query
    if keyword:
        payload_dict["query"] = keyword
    
    # 添加 filter 来指定对象类型
    if obj_type:
        payload_dict["filter"] = {"value": obj_type, "property": "object"}
    
    payload = json.dumps(payload_dict)
    
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
            # 页面的标题在 properties.title.title 数组中
            title_array = item.get("properties", {}).get("title", {}).get("title", [])
            if title_array:
                title = title_array[0].get("plain_text", "")
        elif item["object"] == "database":
            # 数据库的标题直接在 title 数组中
            title_array = item.get("title", [])
            if title_array:
                title = title_array[0].get("plain_text", "")
        
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


# ==================== Rich Text 构建工具 ====================
# 全局变量：临时存储正在构建的 rich_text 列表
_rich_text_buffer = []


def clear_rich_text():
    """清空 rich_text 缓冲区（内部使用，不暴露给 LLM）"""
    global _rich_text_buffer
    _rich_text_buffer = []


def append_text(text: str, bold: bool = False):
    """
    直接添加文本到 rich_text 缓冲区

    Args:
        text: 文本内容
        bold: 是否加粗，默认为 False

    Returns:
        操作状态信息
    """
    global _rich_text_buffer
    element = {
        "type": "text",
        "text": {
            "content": text
        },
        "annotations": {
            "bold": bold
        }
    }
    _rich_text_buffer.append(element)
    return {
        "status": "success",
        "message": f"Text added. Buffer now has {len(_rich_text_buffer)} elements",
        "current_count": len(_rich_text_buffer)
    }


def append_page_mention(page_id: str):
    """
    直接添加页面引用到 rich_text 缓冲区

    Args:
        page_id: Notion 页面的 ID

    Returns:
        操作状态信息
    """
    global _rich_text_buffer
    element = {
        "type": "mention",
        "mention": {
            "type": "page",
            "page": {
                "id": page_id
            }
        }
    }
    _rich_text_buffer.append(element)
    return {
        "status": "success",
        "message": f"Page mention added. Buffer now has {len(_rich_text_buffer)} elements",
        "current_count": len(_rich_text_buffer)
    }


def finish_rich_text():
    """
    完成 rich_text 构建，返回完整列表

    Returns:
        完整的 rich_text 列表
    """
    global _rich_text_buffer
    result = _rich_text_buffer.copy()
    return {
        "status": "finished",
        "message": f"Rich text construction finished with {len(result)} elements",
        "element_count": len(result),
        "rich_text": result
    }


def get_rich_text_buffer():
    """获取当前缓冲区内容（用于调试）"""
    global _rich_text_buffer
    return {
        "count": len(_rich_text_buffer),
        "buffer": _rich_text_buffer
    }


if __name__ == "__main__":
   # 示例 1：生成包含最近修改页面的 rich_text
   # prompt = """
   # 请帮我生成一个 rich_text，内容如下：
   # 1. 先显示粗体文本 "最近修改的页面："
   # 2. 获取最近 5 个修改的页面
   # 3. 为每个页面创建一个换行，然后显示页面的 mention 链接
   # 4. 最后显示文本 "以上是最近的更新"
   # """
   # generate_rich_text(prompt)

   # 示例 2：向智能体提问

   # 测试搜索功能 - 注意参数顺序：keyword, obj_type, limit
   a = search_pages('', 'page', 10)
   print("搜索结果:")
   print(a)


   url = get_lasted_change_page_id(10)
   print("获取到最近修改的页面 ID:")
   print(url)

   rich_text = [
      wrap_text("前面的文本哈哈哈\n", True),
      wrap_text("第一处修改", False),
      wrap_url(url[0]),
      wrap_text("\n第二处修改", False),
      wrap_url(url[1]),
      wrap_text("\n后面的文本", False)
   ]

   change_block(rich_text)




   # page_content=get_page_content("2a319740-7c23-8004-b792-f09b1c282df0")

   
