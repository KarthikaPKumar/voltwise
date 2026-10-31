"""Launch the local edition without creating a login/background service."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
MODEL = os.environ.get('VOLTWISE_OLLAMA_MODEL', 'qwen2.5:7b')

def tags():
    try:
        r = httpx.get('http://127.0.0.1:11434/api/tags', timeout=2, trust_env=False)
        r.raise_for_status()
        return [m['name'] for m in r.json()['models']]
    except (httpx.HTTPError, KeyError, ValueError):
        return None

def main():
    if not (ROOT/'warehouse/voltwise.duckdb').exists():
        subprocess.run([sys.executable, str(ROOT/'scripts/build_analytics.py')], check=True)
    owned = None
    api = None
    try:
        if tags() is None:
            executable = shutil.which('ollama') or '/opt/homebrew/bin/ollama'
            if not Path(executable).exists():
                raise RuntimeError('Install Ollama first: https://ollama.com/download')
            owned = subprocess.Popen([executable, 'serve'], env=dict(os.environ,
                OLLAMA_HOST='127.0.0.1:11434', OLLAMA_NO_CLOUD='1'))
            for _ in range(30):
                if tags() is not None: break
                if owned.poll() is not None: raise RuntimeError('Ollama stopped during startup.')
                time.sleep(1)
        available = tags()
        if available is None or MODEL not in available:
            raise RuntimeError(f'Model missing. Run: ollama pull {MODEL}')
        print(f'Voltwise local AI: {MODEL}\nOpen http://127.0.0.1:8766/#local-agent\nKeep this window open. Press Control-C to stop.', flush=True)
        api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'service.api:app',
                                '--host', '127.0.0.1', '--port', '8766'], cwd=ROOT,
                               env=dict(os.environ, VOLTWISE_OLLAMA_MODEL=MODEL))
        code = api.wait()
        if code: raise RuntimeError('The local web service stopped. Check the output above.')
    except KeyboardInterrupt:
        pass
    finally:
        for process in [api, owned]:
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill()

if __name__ == '__main__': main()
