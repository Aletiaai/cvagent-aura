# This new top-level main.py might just be a simple script to start the web server, or for specific CLI utility tasks if needed.

import config
import uvicorn

if __name__ == "__main__":
    prompts = config.load_all_prompts() # Load prompts on startup
    print(f"Estos son los prompts cargados:\n{prompts}")
    # --- Your CLI application logic starts here ---
    print("CLI App Started. Access prompts via config.PROMPTS")
    # Example: print(config.PROMPTS.get("ask_user_question"))
    uvicorn.run("web_app.main:app", host="127.0.0.1", port=8000, reload=True)
