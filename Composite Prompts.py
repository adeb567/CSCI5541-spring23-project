# -*- coding: utf-8 -*-
"""Score Test.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ZCjGYE7ANHQOYhY-XCHuEktnGcnHYG13
"""

!pip3 install transformers
!pip install sentencepiece
!pip3 install datasets
!pip3 install torch
!pip3 install nlp
!pip3 install rouge_score
!pip3 install py7zr
!pip install --upgrade gspread

from google.colab import auth
import gspread
from google.auth import default
from oauth2client.client import GoogleCredentials

auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)

import pandas as pd
import numpy as np

worksheet = gc.open('Score Test').sheet1
rows = worksheet.get_all_values()
df = pd.DataFrame(rows)

df.columns = df.iloc[0]
df = df.iloc[1:]
#df.head()
#df.columns

from transformers import T5Tokenizer, T5ForConditionalGeneration, AutoTokenizer, AutoModelForCausalLM, LogitsProcessorList, MinLengthLogitsProcessor
import torch

tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-large")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-large")

"""Perplexity, BLEU, ROUGE Score, F1 Score, Human Eval"""

from rouge_score import rouge_scorer
import nltk
from nltk.translate.bleu_score import corpus_bleu, SmoothingFunction
from transformers import pipeline

nltk.download('punkt')

def calculate_likelihood(sentence, model, tokenizer):
    """Calculates the likelihood of a sentence using a language model."""
    input_ids = tokenizer.encode(sentence, return_tensors='pt')
    with torch.no_grad():
        outputs = model.generate(input_ids=input_ids)
    generated_sequence = tokenizer.decode(outputs[0], skip_special_tokens=True)
    generated_input_ids = tokenizer.encode(generated_sequence, return_tensors='pt')
    with torch.no_grad():
        outputs = model(input_ids=input_ids, decoder_input_ids=generated_input_ids[:, :-1])
    logits = outputs.logits[0, -1, :]
    probs = torch.softmax(logits, dim=0).cpu().numpy()
    log_prob = np.log(probs[generated_input_ids[0][-1]])
    return np.exp(log_prob)


def calculate_perplexity(sentence, model, tokenizer):
    """Calculates the perplexity of a sentence using a language model."""
    input_ids = tokenizer.encode(sentence, return_tensors='pt')
    with torch.no_grad():
        outputs = model.generate(input_ids=input_ids)
    generated_sequence = tokenizer.decode(outputs[0], skip_special_tokens=True)
    generated_input_ids = tokenizer.encode(generated_sequence, return_tensors='pt')
    with torch.no_grad():
        outputs = model(input_ids=input_ids, decoder_input_ids=generated_input_ids)
    logits = outputs.logits[0, :-1]
    target = generated_input_ids[0, 1:]
    loss = torch.nn.functional.cross_entropy(logits, target, reduction='none')
    perplexity = torch.exp(torch.mean(loss)).item()
    return perplexity


def calculate_confidence_score(generated_summary, reference_summary):
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = scorer.score(generated_summary, reference_summary)
    confidence = max(scores["rouge1"].fmeasure, scores["rouge2"].fmeasure, scores["rougeL"].fmeasure)
    return confidence

for col in range(np.array(rows).shape[1]):
  if rows[0][col] == 'Prompts':
    prompt = col
  elif rows[0][col] == 'Responses':
    respo = col
  elif rows[0][col] == 'Likelihood':
    like = col
  elif rows[0][col] == 'Perplexity':
    perp = col
  elif rows[0][col] == 'Confidence Score':
    conf = col
  elif rows[0][col] == 'Both Task Achieved':
    bta = col
  elif rows[0][col] == 'Both Task Failed':
    btf = col
  elif rows[0][col] == 'Single Task Achieved':
    sta = col

"""Text Generation and Sentiment Analysis"""

for iter in range(1, 26):
    input_text = rows[iter][prompt]
    input_ids = tokenizer(input_text, return_tensors="pt").input_ids
    outputs = model.generate(input_ids, top_p=0.8, do_sample=True, pad_token_id = model.config.eos_token_id,min_length=50, max_length=250)
    generated_sequence = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    gen = generated_sequence[0]

    df['Responses'][iter]= gen
    df['Likelihood'][iter] = str(calculate_likelihood(gen, model, tokenizer))
    df['Perplexity'][iter] = str(calculate_perplexity(gen, model, tokenizer))
    df['Confidence Score'][iter] = str(calculate_confidence_score(gen, input_text))

"""Text Summarization and Text Generation"""

for iter in range(26, 51):
  input_text = rows[iter][prompt]
  input_ids = tokenizer(input_text, return_tensors="pt").input_ids
  outputs = model.generate(input_ids, top_p=0.8, do_sample=True, pad_token_id = model.config.eos_token_id,min_length=50, max_length=250)
  generated_sequence = tokenizer.batch_decode(outputs, skip_special_tokens=True)
  gen = generated_sequence[0]

  df['Responses'][iter]= gen
  df['Likelihood'][iter] = str(calculate_likelihood(gen, model, tokenizer))
  df['Perplexity'][iter] = str(calculate_perplexity(gen, model, tokenizer))
  df['Confidence Score'][iter] = str(calculate_confidence_score(gen, input_text))

"""Text Summarization and Sentiment Analysis"""

for iter in range(51, 71):
  input_text = rows[iter][prompt]
  input_ids = tokenizer(input_text, return_tensors="pt").input_ids
  outputs = model.generate(input_ids, top_p=0.8, do_sample=True, pad_token_id = model.config.eos_token_id,min_length=50, max_length=1000)
  generated_sequence = tokenizer.batch_decode(outputs, skip_special_tokens=True)
  gen = generated_sequence[0]

  df['Responses'][iter]= gen
  df['Likelihood'][iter] = str(calculate_likelihood(gen, model, tokenizer))
  df['Perplexity'][iter] = str(calculate_perplexity(gen, model, tokenizer))
  df['Confidence Score'][iter] = str(calculate_confidence_score(gen, input_text))

updatedlist = df.to_numpy().tolist()
print(updatedlist)
headers = df.columns.to_list()
dataToWrite = [headers] + updatedlist
worksheet.update(None, dataToWrite)