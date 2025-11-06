import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from app import (
    get_lasted_change_page_id,
    get_page_content,
    wrap_url,
    wrap_text,
    change_block
)

# 加载环境变量
load_dotenv()

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL").replace("/chat/completions", "")
)

# 定义可用的工具函数
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_lasted_change_page_id",
            "description": "获取 Notion 中最近修改的页面 ID 列表，按最后编辑时间降序排序",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_size": {
                        "type": "integer",
                        "description": "要返回的页面数量，默认为 10"
                    }
                },
                "required": ["page_size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_content",
            "description": "获取指定 Notion 页面的所有子 block 内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Notion 页面的 ID"
                    }
                },
                "required": ["page_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wrap_url",
            "description": "将 Notion 页面 ID 包装成 mention 格式，用于在 rich_text 中引用页面",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Notion 页面的 ID"
                    }
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wrap_text",
            "description": "将文本包装成 Notion rich_text 格式，支持粗体等样式",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要包装的文本内容"
                    },
                    "bold": {
                        "type": "boolean",
                        "description": "是否加粗，默认为 false"
                    }
                },
                "required": ["text"]
            }
        }
    }
]

# 函数映射
available_functions = {
    "get_lasted_change_page_id": get_lasted_change_page_id,
    "get_page_content": get_page_content,
    "wrap_url": wrap_url,
    "wrap_text": wrap_text,
}


def run_agent(user_prompt: str, max_iterations: int = 10):
    """
    运行智能体，根据用户提示生成 rich_text

    Args:
        user_prompt: 用户的需求描述
        max_iterations: 最大迭代次数，防止无限循环

    Returns:
        生成的 rich_text 列表
    """
    messages = [
        {
            "role": "system",
            "content": """你是一个 Notion 助手，可以帮助用户生成 Notion rich_text 格式的内容。

你可以使用以下工具：
1. get_lasted_change_page_id - 获取最近修改的页面
2. get_page_content - 获取页面内容
3. wrap_url - 将页面 ID 包装成 mention 格式
4. wrap_text - 将文本包装成 rich_text 格式

你的任务是根据用户需求，调用这些工具，最终生成一个 rich_text 列表。

rich_text 格式示例：
[
  {
    "type": "text",
    "text": { "content": "前面文本\\n" },
    "annotations": { "bold": true }
  },
  {
    "type": "mention",
    "mention": {
      "type": "page",
      "page": { "id": "2a319740-7c23-8004-b792-f09b1c282df0" }
    }
  },
  {
    "type": "text",
    "text": { "content": "\\n后面文本" }
  }
]

工作流程：
1. 先调用 get_lasted_change_page_id 或 get_page_content 获取数据
2. 然后使用 wrap_text 和 wrap_url 按顺序构建每个元素
3. 确保所有的 wrap_* 调用按照最终显示顺序进行
4. 换行使用 \\n，粗体文本设置 bold=true

重要：你必须使用工具函数来构建每个元素，不要直接返回 JSON！"""
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    iteration = 0
    rich_text_result = []

    while iteration < max_iterations:
        iteration += 1
        print(f"\n=== 迭代 {iteration} ===")

        # 调用 OpenAI API
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL"),
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        messages.append(response_message)

        # 检查是否需要调用工具
        tool_calls = response_message.tool_calls

        if not tool_calls:
            # 没有工具调用，说明已完成
            print("智能体完成，返回结果")
            final_content = response_message.content

            # 尝试从响应中提取 rich_text
            if final_content:
                print(f"最终响应: {final_content}")
                # 如果响应包含 JSON，尝试解析
                try:
                    # 查找 JSON 数组
                    import re
                    json_match = re.search(r'\[.*\]', final_content, re.DOTALL)
                    if json_match:
                        rich_text_result = json.loads(json_match.group())
                except:
                    pass

            break

        # 执行工具调用
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"调用函数: {function_name}")
            print(f"参数: {function_args}")

            if function_name in available_functions:
                function_to_call = available_functions[function_name]

                # 调用函数
                try:
                    function_response = function_to_call(**function_args)

                    # 将函数响应转换为字符串
                    if isinstance(function_response, (dict, list)):
                        function_response_str = json.dumps(function_response, ensure_ascii=False)
                    else:
                        function_response_str = str(function_response)

                    print(f"函数返回: {function_response_str[:200]}...")

                    # 将函数响应添加到消息中
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response_str
                    })

                    # 如果是 wrap_* 函数，收集结果
                    if function_name in ["wrap_url", "wrap_text"]:
                        rich_text_result.append(function_response)

                except Exception as e:
                    print(f"函数调用错误: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Error: {str(e)}"
                    })

    return rich_text_result


def generate_rich_text(prompt: str):
    """
    根据提示生成 rich_text 并更新 Notion block

    Args:
        prompt: 用户的需求描述
    """
    print(f"用户需求: {prompt}\n")

    # 运行智能体
    rich_text = run_agent(prompt)

    if rich_text:
        print("\n=== 生成的 Rich Text ===")
        print(json.dumps(rich_text, indent=2, ensure_ascii=False))

        # 更新 Notion block
        print("\n=== 更新 Notion Block ===")
        change_block(rich_text)
        print("✓ 已成功更新 Notion block")
    else:
        print("未能生成 rich_text")

    return rich_text


if __name__ == "__main__":
    # 示例：让智能体生成包含最近修改页面的 rich_text
    prompt = """
    请帮我生成一个 rich_text，内容如下：
    1. 先显示粗体文本 "最近修改的页面："
    2. 获取最近 5 个修改的页面
    3. 为每个页面创建一个换行，然后显示页面的 mention 链接
    4. 最后显示文本 "以上是最近的更新"
    """

    generate_rich_text(prompt)
