import os
import pathlib
import textwrap
from dotenv import load_dotenv
# Used to securely store your API key
import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown

load_dotenv()
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

for m in genai.list_models():
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)

# for text
model = genai.GenerativeModel('gemini-1.0-pro')

# response = model.generate_content("What is the meaning of life?")
# to_markdown(response.text)
# print(response.prompt_feedback)
# print(response.candidates)

file_path = "C:\\Users\\ASUS\\Desktop\\jd_jobsdb.txt"
with open(file_path, "r", encoding="utf-8") as file:
    prompt_text = file.read()

response = model.generate_content(prompt_text)
display(to_markdown(response.text))
print(response.text)
# print(response.prompt_feedback)
# print(response.candidates)