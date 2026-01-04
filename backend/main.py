import json
import os
import time
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORIES_DIR = os.path.join(BASE_DIR, "data", "stories")
USER_FILE = os.path.join(BASE_DIR, "data", "user.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "data", "progress.json")
HEART_REGEN_SECONDS = 4 * 3600

# --- ХЕЛПЕРЫ ---

def get_user_profile():
    if not os.path.exists(USER_FILE):
        save_user_profile({"hearts": 3, "max_hearts": 3, "last_regen_time": 0})
    with open(USER_FILE, "r", encoding="utf-8") as f:
        user = json.load(f)
    # Регенерация
    now = time.time()
    if user["hearts"] < user["max_hearts"]:
        time_passed = now - user.get("last_regen_time", 0)
        add = int(time_passed // HEART_REGEN_SECONDS)
        if add > 0:
            user["hearts"] = min(user["max_hearts"], user["hearts"] + add)
            user["last_regen_time"] = now - (time_passed % HEART_REGEN_SECONDS)
            save_user_profile(user)
    return user

def save_user_profile(data):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- НОВОЕ: Работа с прогрессом ---
def get_story_progress(story_id):
    if not os.path.exists(PROGRESS_FILE):
        return {}
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        all_progress = json.load(f)
    return all_progress.get(story_id, {})

def save_story_progress(story_id, new_state):
    if not os.path.exists(PROGRESS_FILE):
        all_progress = {}
    else:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            all_progress = json.load(f)
    
    # Берем старый прогресс и обновляем его новыми данными (merge)
    current_progress = all_progress.get(story_id, {})
    current_progress.update(new_state)
    all_progress[story_id] = current_progress
    
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_progress, f, indent=2, ensure_ascii=False)

# Поиск пути (как раньше)
def find_story_path(story_id):
    for item in os.listdir(STORIES_DIR):
        p = os.path.join(STORIES_DIR, item)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "manifest.json")):
            with open(os.path.join(p, "manifest.json"), "r", encoding="utf-8") as f:
                if json.load(f).get("id") == story_id: return p
    return None

# --- API ---

@app.post("/api/debug/reset_hearts")
def debug_reset_hearts():
    # 1. Сброс профиля (сердца)
    save_user_profile({"hearts": 3, "max_hearts": 3, "last_regen_time": 0})
    
    # 2. Сброс прогресса историй (удаляем файл сохранений)
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        
    return {"status": "ok", "message": "Full reset completed"}

@app.get("/api/user")
def api_get_user():
    u = get_user_profile()
    wait = 0
    if u["hearts"] < u["max_hearts"]:
        wait = max(0, HEART_REGEN_SECONDS - (time.time() - u["last_regen_time"]))
    return {**u, "next_heart_in": wait}

@app.get("/api/library")
def get_library():
    lib = []
    if os.path.exists(STORIES_DIR):
        for item in os.listdir(STORIES_DIR):
            p = os.path.join(STORIES_DIR, item)
            if os.path.isdir(p) and os.path.exists(os.path.join(p, "manifest.json")):
                try:
                    with open(os.path.join(p, "manifest.json"), "r", encoding="utf-8") as f:
                        d = json.load(f)
                        lib.append({"id": d.get("id"), "title": d.get("title"), "cover": d.get("cover")})
                except: pass
    return lib

@app.get("/api/story/{story_id}/manifest")
def get_manifest(story_id: str):
    p = find_story_path(story_id)
    if not p: raise HTTPException(404, "Not found")
    with open(os.path.join(p, "manifest.json"), "r", encoding="utf-8") as f: return json.load(f)

# СТАРТ ЭПИЗОДА (Списание + Загрузка сохранений)
@app.post("/api/story/{story_id}/{episode_id}/start")
def start_episode(story_id: str, episode_id: str):
    # 1. Списание сердца
    u = get_user_profile()
    if u["hearts"] <= 0: raise HTTPException(400, "No hearts")
    u["hearts"] -= 1
    if u["hearts"] == u["max_hearts"] - 1: u["last_regen_time"] = time.time()
    save_user_profile(u)

    # 2. Поиск файла
    p = find_story_path(story_id)
    if not p: raise HTTPException(404, "Story not found")
    
    with open(os.path.join(p, "manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    ep_file = next((ep["file"] for s in manifest.get("seasons",[]) for ep in s.get("episodes",[]) if ep["id"] == episode_id), None)
    if not ep_file: raise HTTPException(404, "Episode not found")
    
    with open(os.path.join(p, "episodes", ep_file), "r", encoding="utf-8") as f:
        ep_data = json.load(f)

    # 3. МАГИЯ: Объединяем начальное состояние эпизода с сохранениями игрока
    # Сначала берем то, что прописано в json (дефолт)
    final_state = ep_data.get("initial_state", {}).copy()
    # Сверху накатываем то, что игрок уже накопил
    saved_state = get_story_progress(story_id)
    final_state.update(saved_state)

    # Подменяем state в ответе
    ep_data["initial_state"] = final_state
    
    return ep_data

# НОВОЕ: Сохранение прогресса (вызывается фронтендом после каждого выбора)
@app.post("/api/story/{story_id}/save")
def sync_progress(story_id: str, state: dict = Body(...)):
    save_story_progress(story_id, state)
    return {"status": "saved"}