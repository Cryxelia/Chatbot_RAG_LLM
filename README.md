# chatbot_RAG_LLM
This is one of my projects from my LIA and the purpose of this project was to test build a chatbot that could save conversations. But it dosent't include a real login with security. The login is just for test to save a conversation for a user. The chatbot is a RAG-LLM which also has a long-term and short-term memory. The source document for the RAG is "Statliga värdegrunden" and another document containing some excerices to implement "Statliga värdegrunden".

## Requirements
Python
Tested with python version `3.11.9` but others may work.
For this project you need to have [MySQL Workbench](https://downloads.mysql.com/archives/workbench/) and i used version `8.0.40`.
You also need to have a [openai key](https://platform.openai.com/api-keys) and a qdrant api key which you can get for free by register on their [website](https://login.cloud.qdrant.io/u/login/identifier?state=hKFo2SBteGphQTRrdnFDLWU5UmY3NnlHUEpwSEltWEF0UkV3VaFur3VuaXZlcnNhbC1sb2dpbqN0aWTZIHNHRU12RkxobmhDWTJ5UUJQT2dHcGJMZlhtRDZSTk9io2NpZNkgckkxd2NPUEhPTWRlSHVUeDR4MWtGMEtGZFE3d25lemc)


## How to start the app local
1. Clone the project with `git clone [repo name]`
2. Create venv with `python -m venv venv` in the python folder
3. Use the terminal to activate venv with `venv\Scripts\activate` on windows or `source venv/bin/activate`on macOS/Linux
4. You have to be in the root folder to Install dependencies with `pip install -r requirements.txt`
5. Create an `.env` file in the root folder with yor api key for OpenAI in the root of the project and create `OPENAI_API_KEY` variable with your key
6. Add `QDRANT_API_KEY` to your `.env` file for the Qdrant vector database.
7. You also have to add `QDRANT_URL`, `QDRANT_COLLECTION` and `SECRET_KEY` to the `.env` file
8. Then you have to set `LOCAL_DB_PW` and add to the `.env`
9. Open MySQL workbench to create a database for you project with the comand `CREATE SCHEMA save_chat_db;`
10. You also have to migrate the database. To migrate use the comand `python manage.py makemigrations` and `python manage.py migrate`.

### Running the app local
Start the app with `python manage.py runserver`
