# chatbot_with_history_login
This is one of my projects from my LIA and the purpose of this project was to test build a chatbot that could save conversations. But it dosent't include a real login with security. The login is just for test to save a conversation for a user. The chatbot is a RAG-LLM which also has a long-term and short-term memory. The source document for the RAG is "Statliga värdegrunden" and another document containing some excerices to implement "Statliga värdegrunden".
 

## How to start the app local

1. Colne the project with `git clone [repo name]`
2. Create venv with `python -m vemv venv` in the python folder
3. Activate venv with `venv\Scripts\activate` on windows or `source venv/bin/activate`on macOS/Linux
4. Install dependencies with `pip install -r requirements.txt`
5. Create an `.env` file with yor api key for OpenAI in the root of the project and create `OPENAI_API_KEY` variable with your key
6. Add `QDRANT_API_KEY` to your `.env` file for the Qdrant vector database.
7. You also heve to add `QDRANT_URL`, `QDRANT_COLLECTION` to the `.env` file
8.  Sometimses you also have to migrate the database. For that use the comand `python manage.py migrate`.

### Running the app local
Start the app with `python manage.py runserver`
