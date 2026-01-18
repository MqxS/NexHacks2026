# Running AI Stuff

Need to set the following environment variables:
*   `TOKENC_API_KEY` - The API key for the TokenC API.
*   `GEMINI_API_KEY` - The API key for the Gemini API.
*   `WOLFRAM_APP_ID` - The API key for the Wolfram API.

Test $so\varphi$ with the following commands (command-line unit tests):

```
python ai-util/tests/test_utils.py math-calculus-bc
python ai-util/tests/test_utils.py cs1332
python ai-util/tests/test_utils.py ap-gov
```