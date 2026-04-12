本文介绍如何通过兼容 OpenAI 格式的 Chat API 调用千问模型，包括输入输出参数说明及调用示例

SDK 调用配置的`base_url`：`https://dashscope.aliyuncs.com/compatible-mode/v1`

HTTP 请求地址：`POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`

您需要先[获取API Key](https://help.aliyun.com/zh/model-studio/get-api-key)并[配置API Key到环境变量](https://help.aliyun.com/zh/model-studio/configure-api-key-through-environment-variables)。若通过OpenAI SDK进行调用，需要[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)

文本输入

```python
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你是谁？"},
    ]
)
print(completion.model_dump_json())
```

流式输出

```python
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': '你是谁？'}],
    stream=True,
    stream_options={"include_usage": True}
    )
for chunk in completion:
    print(chunk.model_dump_json())
```

图像输入

```python
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-vl-plus",  # 此处以qwen-vl-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[{"role": "user","content": [
            {"type": "image_url",
             "image_url": {"url": "https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg"}},
            {"type": "text", "text": "这是什么"},
            ]}]
    )
print(completion.model_dump_json())
```

工具调用

```python
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 填写DashScope SDK的base_url
)

tools = [
    # 工具1 获取当前时刻的时间
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "当你想知道现在的时间时非常有用。",
            "parameters": {}  # 因为获取当前时间无需输入参数，因此parameters为空字典
        }
    },  
    # 工具2 获取指定城市的天气
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "当你想查询指定城市的天气时非常有用。",
            "parameters": {  
                "type": "object",
                "properties": {
                    # 查询天气时需要提供位置，因此参数设置为location
                    "location": {
                        "type": "string",
                        "description": "城市或县区，比如北京市、杭州市、余杭区等。"
                    }
                },
                "required": ["location"]
            }
        }
    }
]
messages = [{"role": "user", "content": "杭州天气怎么样"}]
completion = client.chat.completions.create(
    model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=messages,
    tools=tools
)

print(completion.model_dump_json())
```

异步调用

```python
import os
import asyncio
from openai import AsyncOpenAI
import platform

client = AsyncOpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

async def main():
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": "你是谁"}],
        model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    )
    print(response.model_dump_json())

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
```

文档理解

```python
import os
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
file_object = client.files.create(file=Path("百炼系列手机产品介绍.docx"), purpose="file-extract")
completion = client.chat.completions.create(
    model="qwen-long",  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[
        {'role': 'system', 'content': f'fileid://{file_object.id}'},
        {'role': 'user', 'content': '这篇文章讲了什么？'}
    ]
)
print(completion.model_dump_json())
```

## **请求体**

\*\*model \*\*\*`string` \***（必选）**

模型名称。

支持的模型：Qwen 大语言模型（商业版、开源版）、Qwen-VL、Qwen-Coder、Qwen-Omni、Qwen-Math。

> Qwen-Audio不支持OpenAI兼容协议，仅支持DashScope协议。

**具体模型名称和计费，请参见**[文本生成-千问](https://help.aliyun.com/zh/model-studio/models#9f8890ce29g5u)。

\*\*messages \*\*\*`array` \***（必选）**

传递给大模型的上下文，按对话顺序排列。

**消息类型**

System Message\*\* \*\*\*`object` \*（可选）

系统消息，用于设定大模型的角色、语气、任务目标或约束条件等。一般放在`messages`数组的第一位。

> QwQ 模型不建议设置 System Message，QVQ 模型设置 System Message不会生效。

**属性**

\*\*content \*\*\*`string` \***（必选）**

系统指令，用于明确模型的角色、行为规范、回答风格和任务约束等。

\*\*role \*\*\*`string` \***（必选）**

系统消息的角色，固定为`system`。

User Message\*\* \*\*\*`object` \***（必选）**

用户消息，用于向模型传递问题、指令或上下文等。

**属性**

**content *`string 或 array `***（必选）

消息内容。若输入只有文本，则为 string 类型；若输入包含图像等多模态数据，或启用显式缓存，则为 array 类型。

**使用多模态模型或启用显式缓存时的属性**

\*\*type \*\*\*`string` \***（必选）**

可选值：

* `text`

  输入文本时需设为`text`。

* `image_url`

  输入图片时需设为`image_url`。

* `input_audio`

  输入音频时需设为`input_audio`。

* `video`

  输入图片列表形式的视频时需设为`video`。

* `video_url`

  输入视频文件时需设为`video_url`。

  > Qwen-VL仅部分模型可输入视频文件，详情参见[视频理解（Qwen-VL）](https://help.aliyun.com/zh/model-studio/vision#80dbf6ca8fh6s)；QVQ与Qwen-Omni 模型支持直接传入视频文件。

\*\*text \*\**`string`*

输入的文本。当`type`为`text`时，是必选参数。

\*\*image\_url \*\**`object`*

输入的图片信息。当`type`为`image_url`时是必选参数。

**属性**

**url** *`string`***（必选）**

图片的 URL或 Base64 Data URL。传入本地文件请参考[图像与视频理解](https://help.aliyun.com/zh/model-studio/vision#647c6397db430)。

\*\*input\_audio \*\**`object`*

输入的音频信息。当`type`为`input_audio`时是必选参数。

**属性**

**data** *`string`***（必选）**

音频的 URL 或Base64 Data URL。传入本地文件请参见：[输入 Base64 编码的本地文件](https://help.aliyun.com/zh/model-studio/qwen-omni#c516d1e824x03)。

**format *`string`***（必选）

输入音频的格式，如`mp3`、`wav`等。

\*\*role \*\*\*`string` \***（必选）**

用户消息的角色，固定为`user`。

Assistant Message \*`object` \*（可选）

模型的回复。通常用于在多轮对话中作为上下文回传给模型。

**属性**

\*\*content \*\*\*`string` \*（可选）

模型回复的文本内容。包含`tool_calls`时，`content`可以为空；否则`content`为必选。

\*\*role \*\*\*`string` \***（必选）**

助手消息的角色，固定为`assistant`。

\*\*partial \*\*\*`boolean` \*（可选）默认值为`false`

是否开启前缀续写。

可选值：

* true：开启；

* false：不开启。

支持的模型参见[前缀续写](https://help.aliyun.com/zh/model-studio/partial-mode)。

**tool\_calls** \*`array` \*（可选）

发起 Function Calling 后，返回的工具与入参信息，包含一个或多个对象。由上一轮模型响应的`tool_calls`字段获得。

**属性**

**id** \*`string` \***（必选）**

工具响应的ID。

**type** *`string`***（必选）**

工具类型，当前只支持设为`function`。

**function** *`object`***（必选）**

工具与入参信息。

**属性**

**name** *`string`***（必选）**

工具名称。

**arguments** *`string`***（必选）**

入参信息，为JSON格式字符串。

**index** *`integer`***（必选）**

当前工具信息在`tool_calls`数组中的索引。

Tool Message \*`object` \*（可选）

工具的输出信息。

**属性**

\*\*content \*\*\*`string` \***（必选）**

工具函数的输出内容，必须为字符串。若工具返回结构化数据（如JSON），需将其序列化为字符串。

\*\*role \*\*\*`string` \***（必选）**

固定为`tool`。

\*\*tool\_call\_id \*\*\*`string` \***（必选）**

发起 Function Calling 后返回的 id，通过completion.choices\[0].message.tool\_calls\[\$index].id获取，用于标记 Tool Message 对应的工具。

stream boolean （可选） 默认值为 false

是否以流式输出方式回复。相关文档：流式输出

可选值：

false：模型生成全部内容后一次性返回；

true：边生成边输出，每生成一部分内容即返回一个数据块（chunk）。需实时逐个读取这些块以拼接完整回复。

推荐设置为true，可提升阅读体验并降低超时风险。

stream_options object （可选）

流式输出的配置项，仅在 stream 为 true 时生效。

属性

include_usage boolean （可选）默认值为false

是否在响应的最后一个数据块包含Token消耗信息。

可选值：

true：包含；

false：不包含。

流式输出时，Token 消耗信息仅可出现在响应的最后一个数据块。
modalities array （可选）默认值为["text"]

输出数据的模态，仅适用于 Qwen-Omni 模型。相关文档：非实时（Qwen-Omni）

可选值：

["text","audio"]：输出文本与音频；

["text"]：仅输出文本。

audio object （可选）

输出音频的音色与格式，仅适用于 Qwen-Omni 模型，且modalities参数需为["text","audio"]。相关文档：非实时（Qwen-Omni）

属性

voice string （必选）

输出音频的音色。请参见非实时（Qwen-Omni）。

format string （必选）

输出音频的格式，仅支持设定为wav。

temperature float （可选）

采样温度，控制模型生成文本的多样性。

temperature越高，生成的文本更多样，反之，生成的文本更确定。

取值范围： [0, 2)

temperature与top_p均可以控制生成文本的多样性，建议只设置其中一个值。更多说明，请参见文本生成模型概述。

temperature默认值

不建议修改QVQ模型的默认temperature值 。
top_p float （可选）

核采样的概率阈值，控制模型生成文本的多样性。

top_p越高，生成的文本更多样。反之，生成的文本更确定。

取值范围：（0,1.0]

temperature与top_p均可以控制生成文本的多样性，建议只设置其中一个值。更多说明，请参见文本生成模型概述。

top_p默认值

不建议修改QVQ模型的默认 top_p 值。
top_k integer （可选）

指定生成过程中用于采样的候选 Token 数量。值越大，输出越随机；值越小，输出越确定。若设为 null 或大于 100，则禁用 top_k 策略，仅 top_p 策略生效。取值必须为大于或等于 0 的整数。

top_k默认值

该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 extra_body 对象中。配置方式为：extra_body={"top_k":xxx}。
不建议修改QVQ模型的默认 top_k 值。
repetition_penalty float （可选）

模型生成时连续序列中的重复度。提高repetition_penalty时可以降低模型生成的重复度，1.0表示不做惩罚。没有严格的取值范围，只要大于0即可。

repetition_penalty默认值

该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 extra_body 对象中。配置方式为：extra_body={"repetition_penalty":xxx}。
使用qwen-vl-plus_2025-01-25模型进行文字提取时，建议设置repetition_penalty为1.0。
不建议修改QVQ模型的默认 repetition_penalty 值。
presence_penalty float （可选）

控制模型生成文本时的内容重复度。

取值范围：[-2.0, 2.0]。正值降低重复度，负值增加重复度。

在创意写作或头脑风暴等需要多样性、趣味性或创造力的场景中，建议调高该值；在技术文档或正式文本等强调一致性与术语准确性的场景中，建议调低该值。

presence_penalty默认值

原理介绍

示例

使用qwen-vl-plus-2025-01-25模型进行文字提取时，建议设置presence_penalty为1.5。
不建议修改QVQ模型的默认presence_penalty值。
response_format object （可选） 默认值为{"type": "text"}

返回内容的格式。可选值：

{"type": "text"}：输出文字回复；

{"type": "json_object"}：输出标准格式的JSON字符串。

相关文档：结构化输出。
若指定为{"type": "json_object"}，需在提示词中明确指示模型输出JSON，如：“请按照json格式输出”，否则会报错。
支持的模型参见结构化输出。
属性

max_tokens integer （可选）

用于限制模型输出的最大 Token 数。若生成内容超过此值，生成将提前停止，且返回的finish_reason为length。

默认值与最大值均为模型的最大输出长度，请参见文本生成-千问。

适用于需控制输出长度的场景，如生成摘要、关键词，或用于降低成本、缩短响应时间。

触发 max_tokens 时，响应的 finish_reason 字段为 length。

max_tokens不限制思考模型思维链的长度。


n integer （可选） 默认值为1

生成响应的数量，取值范围是1-4。适用于需生成多个候选响应的场景，例如创意写作或广告文案。

仅支持 Qwen3（非思考模式）、qwen-plus-character 模型。
若传入 tools 参数， 请将n 设为 1。
增大 n 会增加输出 Token 的消耗，但不增加输入 Token 消耗。
enable_thinking boolean （可选）

使用混合思考（回复前既可思考也可不思考）模型时，是否开启思考模式。适用于 Qwen3.6、Qwen3.5、Qwen3 、Qwen3-Omni-Flash、Qwen3-VL模型。相关文档：深度思考

可选值：

true：开启

开启后，思考内容将通过reasoning_content字段返回。
false：不开启

不同模型的默认值：支持的模型

该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 extra_body 对象中。配置方式为：extra_body={"enable_thinking": xxx}。
preserve_thinking boolean （可选）默认值为 false

是否将对话历史中 assistant 消息的 reasoning_content 拼接至模型输入。适用于需要模型参考历史思考过程的场景。

目前仅支持 qwen3.6-plus、qwen3.6-plus-2026-04-02。

若历史消息中不包含 reasoning_content，开启此参数不会报错，正常兼容。

开启后，历史对话中的 reasoning_content 会计入输入 Token 数量并计费。

该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 extra_body 对象中。配置方式为：extra_body={"preserve_thinking": True}。
thinking_budget integer （可选）

思考过程的最大 Token 数。适用于Qwen3.6、Qwen3.5、Qwen3-VL、Qwen3 的商业版与开源版模型。相关文档：限制思考长度。

默认值为模型最大思维链长度，请参见：模型列表

该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 extra_body 对象中。配置方式为：extra_body={"thinking_budget": xxx}。
enable_code_interpreter boolean （可选）默认值为 false

是否开启代码解释器功能。相关文档：代码解释器

可选值：

true：开启

false：不开启

该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 extra_body 对象中。配置方式为：extra_body={"enable_code_interpreter": xxx}。
seed integer （可选）

随机数种子。用于确保在相同输入和参数下生成结果可复现。若调用时传入相同的 seed 且其他参数不变，模型将尽可能返回相同结果。

取值范围：[0,231−1]。

seed默认值

logprobs boolean （可选）默认值为 false

是否返回输出 Token 的对数概率，可选值：

true

返回

false

不返回

思考阶段生成的内容（reasoning_content）不会返回对数概率。
支持的模型

top_logprobs integer （可选）默认值为0

指定在每一步生成时，返回模型最大概率的候选 Token 个数。

取值范围：[0,5]

仅当 logprobs 为 true 时生效。

stop string 或 array （可选）

用于指定停止词。当模型生成的文本中出现stop 指定的字符串或token_id时，生成将立即终止。

可传入敏感词以控制模型的输出。

stop为数组时，不可将token_id和字符串同时作为元素输入，比如不可以指定为["你好",104307]。
tools array （可选）

包含一个或多个工具对象的数组，供模型在 Function Calling 中调用。相关文档：Function Calling

设置 tools 且模型判断需要调用工具时，响应会通过 tool_calls 返回工具信息。

属性

tool_choice string 或 object （可选）默认值为 auto

工具选择策略。若需对某类问题强制指定工具调用方式（例如始终使用某工具或禁用所有工具），可设置此参数。

可选值：

auto

大模型自主选择工具策略。

none

若不希望进行工具调用，可设定tool_choice参数为none；

{"type": "function", "function": {"name": "the_function_to_call"}}

若希望强制调用某个工具，可设定tool_choice参数为{"type": "function", "function": {"name": "the_function_to_call"}}，其中the_function_to_call是指定的工具函数名称。

思考模式的模型不支持强制调用某个工具。
parallel_tool_calls boolean （可选）默认值为 false

是否开启并行工具调用。相关文档：并行工具调用

可选值：

true：开启

false：不开启

enable_search boolean （可选）默认值为 false

是否开启联网搜索。相关文档：联网搜索

可选值：

true：开启；

若开启后未联网搜索，可优化提示词，或设置search_options中的forced_search参数开启强制搜索。
false：不开启。

启用互联网搜索功能可能会增加 Token 的消耗。
该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 extra_body 对象中。配置方式为：extra_body={"enable_search": True}。
search_options object （可选）

联网搜索的策略。相关文档：联网搜索

属性

该参数非OpenAI标准参数。通过 Python SDK调用时，请放入 extra_body 对象中。配置方式为：extra_body={"search_options": xxx}。
X-DashScope-DataInspection string （可选）

在千问 API 的内容安全能力基础上，是否进一步识别输入输出内容的违规信息。取值如下：

'{"input":"cip","output":"cip"}'：进一步识别；

不设置该参数：不进一步识别。

通过 HTTP 调用时请放入请求头：-H "X-DashScope-DataInspection: {\"input\": \"cip\", \"output\": \"cip\"}"；

通过 Python SDK 调用时请通过extra_headers配置：extra_headers={'X-DashScope-DataInspection': '{"input":"cip","output":"cip"}'}。

详细使用方法请参见输⼊输出 AI 安全护栏。

不支持通过 Node.js SDK设置。


chat响应对象（非流式输出）
id string

本次调用的唯一标识符。

choices array

模型生成内容的数组。

属性

finish_reason string

模型停止生成的原因。

有三种情况：

触发输入参数中的stop参数，或自然停止输出时为stop；

生成长度过长而结束为length；

需要调用工具而结束为tool_calls。

index integer

当前对象在choices数组中的索引。

logprobs object

模型输出的 Token 概率信息。

属性

content array

包含每个 Token 及其对数概率的数组。

属性

token string

当前 Token 的文本。

bytes array

当前 Token 的 UTF‑8 原始字节列表，用于精确还原输出内容（例如表情符号或中文字符）。

logprob float

当前 Token 的对数概率。返回值为 null 表示概率值极低。

top_logprobs array

当前 Token 位置最可能的若干候选 Token，数量与请求参数top_logprobs保持一致。每个元素包含：

属性

message object

模型输出的消息。

属性

content string

模型的回复内容。

reasoning_content string

模型的思维链内容。

refusal string

该参数当前固定为null。

role string

消息的角色，固定为assistant。

audio object

该参数当前固定为null。

function_call（即将废弃）object

该值固定为null，请参考tool_calls参数。

tool_calls array

在发起 Function Calling后，模型生成的工具与入参信息。

属性

id string

本次工具响应的唯一标识符。

type string

工具类型，当前只支持function。

function object

工具信息。

属性

name string

工具名称。

arguments string

入参信息，为JSON格式字符串。

由于大模型响应有一定随机性，输出的入参信息可能不符合函数签名。请在调用前校验参数有效性
index integer

当前工具在tool_calls数组中的索引。

created integer

请求创建时的 Unix 时间戳（秒）。

model string

本次请求使用的模型。

object string

始终为chat.completion。

service_tier string

该参数当前固定为null。

system_fingerprint string

该参数当前固定为null。

usage object

本次请求的 Token 消耗信息。

属性

completion_tokens integer

模型输出的 Token 数。

prompt_tokens integer

输入的 Token 数。

total_tokens integer

消耗的总 Token 数，为prompt_tokens与completion_tokens的总和。

completion_tokens_details object

使用Qwen-VL 模型时输出Token的细粒度分类。

属性

audio_tokens integer

该参数当前固定为null。

reasoning_tokens integer

该参数当前固定为null。

text_tokens integer

Qwen-VL 模型输出文本的Token数。

prompt_tokens_details object

输入 Token 的细粒度分类。

属性

audio_tokens integer

该参数当前固定为null。

cached_tokens integer

命中 Cache 的 Token 数。Context Cache 详情请参见上下文缓存。

text_tokens integer

Qwen-VL 模型输入的文本 Token 数。

image_tokens integer

Qwen-VL 模型输入的图像 Token数。

video_tokens integer

Qwen-VL 模型输入的视频文件或者图像列表 Token 数。

cache_creation object

显式缓存创建信息。

属性

ephemeral_5m_input_tokens integer

创建显式缓存的 Token 数。

cache_creation_input_tokens integer

创建显式缓存的 Token 数。

cache_type string

使用显式缓存时，参数值为ephemeral，否则该参数不存在。

```json
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "我是阿里云开发的一款超大规模语言模型，我叫千问。"
            },
            "finish_reason": "stop",
            "index": 0,
            "logprobs": null
        }
    ],
    "object": "chat.completion",
    "usage": {
        "prompt_tokens": 3019,
        "completion_tokens": 104,
        "total_tokens": 3123,
        "prompt_tokens_details": {
            "cached_tokens": 2048
        }
    },
    "created": 1735120033,
    "system_fingerprint": null,
    "model": "qwen-plus",
    "id": "chatcmpl-6ada9ed2-7f33-9de2-8bb0-78bd4035025a"
}
```


chat响应chunk对象（流式输出）
id string

本次调用的唯一标识符。每个chunk对象有相同的 id。

choices array

模型生成内容的数组，可包含一个或多个对象。若设置include_usage参数为true，则choices在最后一个chunk中为空数组。

属性

delta object

请求的增量对象。

属性

content string

增量消息内容。

reasoning_content string

增量思维链内容。

function_call object

该值默认为null，请参考tool_calls参数。

audio object

使用 Qwen-Omni 模型时生成的回复。

属性

refusal object

该参数当前固定为null。

role string

增量消息对象的角色，只在第一个chunk中有值。

tool_calls array

在发起 Function Calling后，模型生成的工具与入参信息。

属性

index integer

当前工具在tool_calls数组中的索引。

id string

本次工具响应的唯一标识符。

function object

被调用的工具信息。

属性

arguments string

增量的入参信息，所有chunk的arguments拼接后为完整的入参。

由于大模型响应有一定随机性，输出的入参信息可能不符合函数签名。请在调用前校验参数有效性。
name string

工具名称，只在第一个chunk中有值。

type string

工具类型，当前只支持function。

finish_reason string

模型停止生成的原因。有四种情况：

因触发输入参数中的stop参数，或自然停止输出时为stop；

生成未结束时为null；

生成长度过长而结束为length；

需要调用工具而结束为tool_calls。

index integer

当前响应在choices数组中的索引。当输入参数 n 大于1时，需根据本参数进行不同响应对应的完整内容的拼接。

logprobs object

当前对象的概率信息。

属性

created integer

本次请求被创建时的时间戳。每个chunk有相同的时间戳。

model string

本次请求使用的模型。

object string

始终为chat.completion.chunk。

service_tier string

该参数当前固定为null。

system_fingerprintstring

该参数当前固定为null。

usage object

本次请求消耗的Token。只在include_usage为true时，在最后一个chunk显示。

属性

completion_tokens integer

模型输出的 Token 数。

prompt_tokens integer

输入 Token 数。

total_tokens integer

总 Token 数，为prompt_tokens与completion_tokens的总和。

completion_tokens_details object

输出 Token 的详细信息。

属性

audio_tokens integer

Qwen-Omni 模型输出的音频 Token 数。

reasoning_tokens integer

思考过程 Token 数。

text_tokens integer

输出文本 Token 数。

prompt_tokens_details object

输入 Token的细粒度分类。

属性

audio_tokens integer

输入音频的 Token 数。

视频文件中的音频 Token 数通过本参数返回。
text_tokens integer

输入文本的 Token 数。

video_tokens integer

输入视频（图片列表形式或视频文件）的 Token 数。

image_tokens integer

输入图片的 Token 数。

cached_tokens integer

命中缓存的 Token 数。Context Cache 详情请参见上下文缓存。

cache_creation object

显式缓存创建信息。

属性

ephemeral_5m_input_tokens integer

创建显式缓存的 Token 数。

cache_creation_input_tokens integer

创建显式缓存的 Token 数。

cache_type string

缓存类型，固定为ephemeral。


```json
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"","function_call":null,"refusal":null,"role":"assistant","tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"我是","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"来自","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"chatcmpl-e30f5ae7-3063-93c4-90fe-beb5f900bd57","choices":[{"delta":{"content":"阿里","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1735113344,"model":"qwen-plus","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
```


