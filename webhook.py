import tarfile
import time
from fastapi import FastAPI, Header, File, UploadFile, HTTPException, status, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import shutil
from pathlib import Path
import os
from tarfile import TarFile
import uvicorn
import threading
import jinja2
from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Глобальные настройки для таймаута приёма
    """
    global_timeout: int = 2000

    class Config:
        env_prefix = "APP_"


@asynccontextmanager
async def lifespan(app:FastAPI):
    """
    Функция перед запуском сервера запускает всё, что стоит до ключевого слова yield,
    а после выключения сервера - всё, что стоит после. В данной версии перед запуском
    незавершенные загрузки помечаются как ошибки.
    :param app: Приложение FastAPI, к которому применяются действия
    :return: AsyncContextManager[None]
    """
    if not os.path.exists(HOME_PATH):
        os.makedirs(HOME_PATH)
    for file in os.listdir(HOME_PATH):
        if file.startswith("load."):
            os.remove(HOME_PATH.joinpath(file))
            HOME_PATH.joinpath("error" + file[4:]).touch()
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
settings = Settings()

HOME_PATH = Path("~/dev/load").expanduser()
TEMPLATES = Jinja2Templates(directory="static/templates")
TIMEOUT_DICT = {}


@app.post("/webhook/message/{branch}")
async def message(branch: str, state: str = Header(None)):
    """
    Ручка FastAPI
    При поступлении POST-запроса с указанием подготавливаемой ветки запускает таймаут и создаёт файл-индикатор загрузки.
    :param branch: Ветка, которая в скором времени будет загружена
    :param state: Заголовок ветки
    :return: JSONResponse с данными о выполнении функции: успех, ошибка на стороне сервера, неверный запрос
    """
    if branch and state:
        print(f"Preparing {branch}")
        p = f"{HOME_PATH}/{branch}"
        loading = Path(f"{HOME_PATH}/load.{branch}")
        open(loading, 'a').close()
        error = Path(f"{HOME_PATH}/error.{branch}")
        try:
            os.remove(error)
        except FileNotFoundError:
            pass
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        result = put_in_timeout(branch, settings.global_timeout)
        if result:
            return JSONResponse(content={branch: "Success"}, status_code=status.HTTP_202_ACCEPTED)
        else:
            return JSONResponse(content={branch: "Failed to start timeout"},
                                status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    else:
        return JSONResponse(content={"error": "Invalid request"}, status_code=status.HTTP_400_BAD_REQUEST)


def put_in_timeout(branch: str, seconds: int):
    """
    Начинает таймаут для определенной ветки
    :param branch: Ветка
    :param seconds: Длительность таймаута
    :return: True, если всё прошло успешно
    """
    TIMEOUT_DICT[branch] = seconds
    p = threading.Thread(target=countdown_thread, args=(branch,), name="Countdown", daemon=True)
    p.start()
    return True


def countdown_thread(branch):
    """
    Поток, занимающийся отсчётом таймаута
    :param branch: Ветка, за которой сладит счетчик
    :return:
    """
    try:
        while TIMEOUT_DICT[branch] > 0:
            time.sleep(1)
            TIMEOUT_DICT[branch] -= 1
    except KeyError:
        return
    TIMEOUT_DICT.pop(branch)
    os.remove(f"{HOME_PATH}/load.{branch}")
    HOME_PATH.joinpath(f"error.{branch}").touch()
    print(f"Error: {branch} timed out ")


@app.post("/webhook/download/{branch}")
async def load(branch: str, download: str = Header(None), file: UploadFile = File(None)):
    """
    Ручка FastAPI
    При поступлении POST-запроса проверяет, ожидается ли загрузка этой ветки. Если да - загружает её как .tar архив,
    распаковывает и удаляет файл-индикатор загрузки
    :param branch: Ветка, которая загружается
    :param download: Заголовок с True
    :param file: Данные ветки, передаваемые на сервер
    :return:
    """
    try:
        TIMEOUT_DICT.pop(branch)
    except KeyError:
        return JSONResponse(content={"error": f"{branch} timed out or was not requested"},
                            status_code=status.HTTP_408_REQUEST_TIMEOUT)

    if download and file:
        p = HOME_PATH.joinpath(branch)
        os.makedirs(p, exist_ok=True)
        local_path = Path(p).joinpath(file.filename)
        with local_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            try:
                with TarFile(local_path, 'r') as tar_ref:
                    tar_ref.extractall(path=p)
            except tarfile.ReadError:
                return JSONResponse(content={"error": "Invalid or corrupted file"},
                                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
            print(f"File {file.filename} downloaded and extracted to {p}")
            loading = Path(f"{HOME_PATH}/load.{branch}")
            if loading.is_file():
                os.remove(loading)
            return JSONResponse(content={"path": f"{HOME_PATH}/{branch}", branch: "Success"},
                                status_code=status.HTTP_200_OK)
    else:
        return JSONResponse(content={"error": "Invalid request"}, status_code=status.HTTP_400_BAD_REQUEST)


@app.get("/{branch}/{p:path}")
async def get(branch: str, p: str, request: Request):
    """
    Ручка FastAPI
    Возвращает указанную страницу при её наличии, при отсутствии - возвращает "заглушку" с указанием причины: обновление
    ветки, либо ошибка.
    :param branch: Ветка
    :param p: Путь до файла в ветке
    :param request: Автоматически заполняемый параметр
    :return:
    """
    if branch == "favicon.ico":
        return HTTPException(status_code=404, detail="No favicon.ico provided")
    file = HOME_PATH.joinpath(branch, "html", p)
    loading = Path(f"{HOME_PATH}/load.{branch}")
    error = Path(f"{HOME_PATH}/error.{branch}")
    try:
        if loading.is_file():
            return TEMPLATES.TemplateResponse("branch_uploading.html", {"request": request, "branch": branch},
                                              status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        elif error.is_file():
            return TEMPLATES.TemplateResponse("upload_error.html",
                                              {"request": request,
                                               "error_name": f"Ошибка загрузки {branch}",
                                               "error_context": f"При загрузке {branch} произошла ошибка"},
                                              status_code=status.HTTP_404_NOT_FOUND)

        elif file.exists():
            return FileResponse(file, status_code=status.HTTP_200_OK)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    except Exception as e:
        if type(e) == FileNotFoundError or type(e) == HTTPException:
            return TEMPLATES.TemplateResponse("upload_error.html",
                                              {"request": request,
                                               "error_name": f"Ошибка загрузки файла",
                                               "error_context": f"При загрузке файла {file} произошла ошибка"},
                                              status_code=status.HTTP_404_NOT_FOUND)
        else:
            return TEMPLATES.TemplateResponse("upload_error.html",
                                              {"request": request,
                                               "error_name": f"Ошибка - {str(type(e).__name__)}",
                                               "error_context": '\n'.join(map(str, e.args))},
                                              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)       


@app.get("/")
def read_root(request: Request):
    names = []
    for entry in os.listdir(HOME_PATH):
        entry_path = os.path.join(HOME_PATH, entry)
        if os.path.isdir(entry_path):
            names.append(entry)
        elif entry.startswith("load.") or entry.startswith("error."):
            _, _, suffix = entry.partition(".")
            names.append(suffix)
    return TEMPLATES.TemplateResponse("index.html", {"request": request, "names": names}, status_code=status.HTTP_200_OK)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
