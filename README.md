# AI LLM Course

Code examples for the AI LLM course. Each numbered folder (`1. intro`, `2. openai-intro`, ...) holds the examples for one lesson.

## What you need

Install these before you start:

- **Python 3**: download it from [python.org](https://www.python.org/downloads/). Check that it works by running `python --version` (or `python3 --version` on macOS/Linux).
- **Git**: download it from [git-scm.com](https://git-scm.com/downloads). Check it with `git --version`.
- **A code editor** of your choice, for example [VS Code](https://code.visualstudio.com/) or [PyCharm](https://www.jetbrains.com/pycharm/).
- **A virtual environment** (recommended). It keeps this course's packages separate from the rest of your computer. The steps below set one up for you.
- **ffmpeg** (only for the audio examples in `8. langchain-fundamentals`: `voice_assis.py` and `yt_vid_summarizer.py`). Whisper uses it to read audio files. Install it with:
  - **Windows:** `winget install --id Gyan.FFmpeg`
  - **macOS:** `brew install ffmpeg` (needs [Homebrew](https://brew.sh/))
  - **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`

  Check it with `ffmpeg -version`.

## First-time setup

Run these commands in a terminal (on Windows, use Command Prompt or PowerShell).

1. Download the project and go into its folder:

   ```bash
   git clone https://github.com/higgs-labs/ai-llm-course.git
   cd ai-llm-course
   ```

2. Create a virtual environment called `venv`:

   ```bash
   python -m venv venv
   ```

   On macOS/Linux, use `python3` instead of `python` if `python` is not found.

3. Activate the virtual environment:

   - **Windows:**

     ```bash
     venv\Scripts\activate
     ```

   - **macOS/Linux:**

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
cd ai-llm-course
git pull
```

Then activate your virtual environment (step 3 above) and install any new packages:

```bash
pip install -r requirements.txt
```

## Every time you open a new terminal

The virtual environment is only active in the terminal where you activated it. When you open a new terminal, go into the project folder and activate it again (step 3 above) before running any code.
