from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

completion = client.chat.completions.create(
  model="openai/gpt-5.2",
  messages=[
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
)

print(completion.choices[0].message.content)
