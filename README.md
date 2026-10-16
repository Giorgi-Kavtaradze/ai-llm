# AI LLM

## What you need

Install these before you start:

* **Python 3**: download it from [python.org](https://www.python.org/downloads/). Check that it works by running `python --version` (or `python3 --version` on macOS/Linux).
* **Git**: download it from [git-scm.com](https://git-scm.com/downloads). Check it with `git --version`.
* **A code editor** of your choice, for example [VS Code](https://code.visualstudio.com/) or [PyCharm](https://www.jetbrains.com/pycharm/).
* **A virtual environment** (recommended). It keeps this course's packages separate from the rest of your computer. The steps below set one up for you.
* **ffmpeg** (only for the audio examples in `8. langchain-fundamentals`: `voice_assis.py` and `yt_vid_summarizer.py`). Whisper uses it to read audio files. Install it with:

  * **Windows:** `winget install --id Gyan.FFmpeg`
  * **macOS:** `brew install ffmpeg` (needs [Homebrew](https://brew.sh/))
  * **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`

  Check it with `ffmpeg -version`.

## First-time setup

Run these commands in a terminal (on Windows, use Command Prompt or PowerShell).

1. Download the project and go into its folder:

   ```bash
   git clone https://github.com/Giorgi-Kavtaradze/ai-llm.git
   cd ai-llm
   ```

2. Create a virtual environment called `venv`:

   ```bash
   python -m venv venv
   ```

   On macOS/Linux, use `python3` instead of `python` if `python` is not found.

3. Activate the virtual environment:

   * **Windows:**

     ```bash
     venv\Scripts\activate
     ```

   * **macOS/Linux:**

     ```bash
     source venv/bin/activate
     ```

   When it is active, you will see `(venv)` at the start of your terminal prompt.

4. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

   This can take several minutes because some packages (such as `torch`) are large.

## If you already downloaded the project

Get the latest changes:

```bash
cd ai-llm
git pull
```

Then activate your virtual environment (step 3 above) and install any new packages:

```bash
pip install -r requirements.txt
```

## Every time you open a new terminal

The virtual environment is only active in the terminal where you activated it. When you open a new terminal, go into the project folder and activate it again (step 3 above) before running any code.

## 12: Google ADK

The `12. ADK` folder has six agents built with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/):

| Folder                   | What it shows                                                                   |
| ------------------------ | ------------------------------------------------------------------------------- |
| `agent_1_ollama`         | A basic agent running on a local Ollama model                                   |
| `agent_2_gemini_tools`   | A Gemini agent with tools (live weather and local time)                         |
| `agent_3_sequential`     | `SequentialAgent`: agents that run one after another                            |
| `agent_4_parallel`       | `ParallelAgent`: agents that run at the same time, then one combines their work |
| `agent_5_session`        | Sessions and state (runs from the terminal)                                     |
| `agent_6_model_callback` | Model callbacks: a profanity filter                                             |

### API keys

Add these lines to the `.env` file in the project root (create the file if it does not exist):

```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-gemini-key
OPENWEATHER_API_KEY=your-openweathermap-key
```

* **`GOOGLE_API_KEY`** is needed by every agent except `agent_1_ollama`. Get one at [Google AI Studio](https://aistudio.google.com/apikey).
* **`OPENWEATHER_API_KEY`** is only needed by `agent_2_gemini_tools`. Get one at [OpenWeatherMap](https://home.openweathermap.org/api_keys).
* **`agent_1_ollama`** needs no key, but needs [Ollama](https://ollama.com/download) running on your computer with the model downloaded: `ollama pull gemma4` (a large download).

### Running the agents

Go into the `12. ADK` folder and start the ADK web UI:

```bash
cd "12. ADK"
adk web
```

Open http://127.0.0.1:8000 in your browser and pick an agent from the dropdown. To chat in the terminal instead, run `adk run agent_1_ollama` (or any other agent folder).

Run `adk web` from the `12. ADK` folder itself, not from inside an agent folder. Otherwise you get "No agents found".

Example 5 runs from the terminal instead of the web UI:

```bash
cd "12. ADK/agent_5_session"
python session_object.py
python agent.py
```

### Deploying to Google Cloud (optional)

`12. ADK/deploy.sh` deploys an agent to Google Cloud Run. Pass the agent folder and your Google Cloud project ID:

```bash
./deploy.sh agent_3_sequential your-project-id
```

If you leave out the project ID, the project set with `gcloud config set project` is used. It needs:

* The [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`)
* A Google Cloud project with billing turned on

The one-time setup commands are at the top of the script. The script runs on macOS/Linux, or in Git Bash on Windows.
