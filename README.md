# Buddy — Empório da Música

Buddy is a text-based customer support prototype for Empório da Música, a
fictional musical instrument store in Campo Grande, Brazil. It chats with
customers through the command line and combines Gemini responses with local
lookups against the store's data.

## Requirements

- Python 3.10 or later
- A Google Gemini API key
- Internet access to communicate with the model

## Setup and usage

Open PowerShell in the project directory and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root and add your API key:

```text
GEMINI_API_KEY=your_api_key
```

`.env` is listed in `.gitignore`. Do not share or publish this file. Then start
the assistant:

```powershell
python agent.py
```

Type `sair` to exit. If PowerShell blocks virtual environment activation, you
can also run commands using `.venv\Scripts\python.exe`.

### Tests

Automated tests use local data and do not require a Gemini API key:

```powershell
python -m unittest
```

To test the provider connection separately, run:

```powershell
python test_api.py
```

This test makes a real request to Gemini and requires a valid API key. The
service may be temporarily unavailable or subject to usage limits.

To regenerate the JSON files from the CSV source data after updates, run:

```powershell
python convert_data.py
```

## Technical decisions

### Interface and model provider

- **Language:** Python, as required by the challenge.
- **Interface:** CLI, chosen because it is easy to run and demonstrates
  conversations without adding a web layer.
- **Provider and model:** Google Gemini API, accessed through the `google-genai`
  library; the code uses `gemini-3.8-flash`.
- **Configuration:** the API key is read from the `GEMINI_API_KEY` environment
  variable, loaded from `.env` with `python-dotenv`. The key is not stored in
  source code.

### Data and context retrieval

The application uses a hybrid approach without an agent framework:

1. **Catalog and promotions:** JSON files in `_data-json_/` are queried locally.
   A simple lexical search compares message terms with product names,
   descriptions, categories, and specifications. It also filters out inactive
   and out-of-stock products, as well as products above the maximum price
   detected in the question. Relevant results are sent to Gemini to formulate
   the response.
2. **Store policies:** the contents of
   `_data-json_/politicas_da_loja.md` are included in the system instructions to
   guide responses about opening hours, payments, exchanges, and returns.
3. **Orders:** order lookup is deterministic and handled locally. The program
   requests the order number and the email address on the order; when both
   match, it returns the status and, when available, the estimated delivery
   date and tracking code. This lookup is not sent to Gemini.

This lexical retrieval approach was chosen because it is lightweight and
suitable for the small catalog provided in the challenge. It does not use
embeddings, a vector database, or semantic RAG.

### Prompt strategy

The prompt in `prompt.py` defines Buddy's friendly persona, limits its scope to
products sold by the store, and instructs the model not to invent prices,
inventory information, or policies. The store manual is the source of truth
for policy-related answers. Order lookups are handled outside the model using
the local validation described above. The agent responds in Portuguese because
the store is located in Brazil and its target customers are primarily
Portuguese speakers.

### Conversation history

Gemini's chat session maintains the conversation history while the process is
running. The history is not persisted to a file or database and is lost when
the program exits.

## Conversation examples

The `Exemplos/` folder contains four illustrative conversations in Portuguese:
catalog lookup, opening hours, a return request, and an out-of-scope request for
accessories. English translations are available in `Examples/en/`.

## Known limitations and next steps

- The provided files contain static demonstration data. Order status,
  inventory, prices, and tracking information may become outdated; there is no
  integration with order management systems or shipping providers.
- Verifying an order with its number and email address is only basic protection
  for this prototype, not strong authentication. In production, I would use an
  authenticated flow and reduce exposure of personal data.
- Catalog search is lexical. Synonyms or unexpectedly phrased questions may
  fail to find all relevant results. With more time, I would evaluate semantic
  search and test against real-world questions.
- The assistant depends on Gemini availability; temporary errors, such as HTTP
  503 responses, are displayed and are not automatically retried.
- The CLI is not connected to WhatsApp or an online store, and conversation
  history is not saved. A next step could add a customer support channel,
  persistence with privacy controls, logging, and limited retries.
- I would expand the tests to cover more search variations, data errors, and
  end-to-end interactions.

## Use of coding assistants

Copilot, integrated into VS Code, was used as a development aid. The assistant
helped clean up the code, prepare and review this README, answer relevant
development questions, and implement improvements accompanied by tests. All
suggestions were reviewed, adapted when needed, and validated locally. The
assistant supported the development process, while the analysis and final
validation of the solution remained my responsibility.
