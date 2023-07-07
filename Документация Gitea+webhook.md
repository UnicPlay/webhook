
## Запуск и настройка локального сервера Gitea
Требования: 
- docker-compose 

Порядок действий:  
1. Создать файл docker-compose.yml со следующим содержанием:  
   ```yaml
      networks:
        giteanet:
          name: giteanet
          driver: bridge
      
      services:
        gitea:
          image: gitea/gitea:nightly
          container_name: gitea
          environment:
            - USER_UID=1000
            - USER_GID=1000
          restart: always
          networks:
            - giteanet
          volumes:
            - ./gitea:/data
            - /etc/timezone:/etc/timezone:ro
            - /etc/localtime:/etc/localtime:ro
          ports:
            - "3000:3000"
            - "222:22"
          stdin_open: true
          tty: true
   ```
      
   Заменить UID и GID на идентификаторы текущего пользователя (команда `id` в терминале)  
2. Запустить этот файл командой `docker-compose up -d` в терминале в папке с этим файлом  
3. Открыть в браузере http://0.0.0.0:3000  
4. Сконфигурировать, нажать "Установить Gitea" в нижней части страницы  
5. Зарегистрировать учетную запись  
6. Войти под учетной записью администратора (если при конфигурации не были созданы учетные записи администраторов, права администратора автоматически присваиваются первой 
   зарегистрированной учётной записи)  
7. Загрузить необходимые репозитории  

В папке с docker-compose после установки появится папка gitea с данными сервера
## Настройка Gitea Actions
Требования:
1. Функционирующий сервер Gitea v1.19.3 или новее с доступом к админ-панели

Установка зависимостей:  
Исполняемый файл раннера - средства выполнения рабочих потоков Gitea Actions  
Скачать [act_runner-nightly-linux-amd64](https://dl.gitea.com/act_runner/nightly/act_runner-nightly-linux-amd64)


Порядок действий:

1. В директории с данными сервера Gitea в файле gitea/gitea/conf/app.ini добавить в конец:

    ```ini
    [actions]
    ENABLED=true
    ```
    После этого на сервере появится возможность пользоваться действиями
2. Запустить или перезапустить сервер (`docker-compose up -d` или `docker-compose down && docker-compose up -d`)

3. В репозитории в правой верхней части зайти в "Настройки", слева вкладка "Репозиторий", 
   чуть ниже середины страницы пункт "Включить действия репозитория" отметить галочкой. 
   Нажать ближайшую снизу кнопку "Обновить настройки"![img.png](https://i.imgur.com/Kz0zg8W.png)

4. В админ-панели либо в настройках репозитория открыть вкладку "Действия" - "Раннеры"
   Кликнуть на "Создать новый раннер" и скопировать оттуда token.  
   1. Если token копируется из админ-панели, раннер будет доступен в любом репозитории в этом экземпляре Gitea.  
   2. Если из настроек репозитория - будет доступен только в этом репозитории.  

5. Дать права исполнения файлу act_runner-nightly-linux-amd64, скачанному во время установки зависимостей (далее он будет обозначаться act-runner) 
   > chmod +x act-runner

6. Сгенерировать базовый конфиг, в последующих шагах он будет использоваться для подстройки раннера
	> ./act-runner generate-config > config.yml
   ```yaml
   # Example configuration file, it's safe to copy this as the default config file without any modification.
   
   log:
     # The level of logging, can be trace, debug, info, warn, error, fatal
     level: info
   
   runner:
     # Where to store the registration result.
     file: .runner
     # Execute how many tasks concurrently at the same time.
     capacity: 1
     # Extra environment variables to run jobs.
     envs:
       A_TEST_ENV_NAME_1: a_test_env_value_1
       A_TEST_ENV_NAME_2: a_test_env_value_2
     # Extra environment variables to run jobs from a file.
     # It will be ignored if it's empty or the file doesn't exist.
     env_file: .env
     # The timeout for a job to be finished.
     # Please note that the Gitea instance also has a timeout (3h by default) for the job.
     # So the job could be stopped by the Gitea instance if it's timeout is shorter than this.
     timeout: 3h
     # Whether skip verifying the TLS certificate of the Gitea instance.
     insecure: false
     # The timeout for fetching the job from the Gitea instance.
     fetch_timeout: 5s
     # The interval for fetching the job from the Gitea instance.
     fetch_interval: 2s
   
   cache:
     # Enable cache server to use actions/cache.
     enabled: true
     # The directory to store the cache data.
     # If it's empty, the cache data will be stored in $HOME/.cache/actcache.
     dir: ""
     # The host of the cache server.
     # It's not for the address to listen, but the address to connect from job containers.
     # So 0.0.0.0 is a bad choice, leave it empty to detect automatically.
     host: ""
     # The port of the cache server.
     # 0 means to use a random available port.
     port: 0
   
   container:
     # Specifies the network to which the container will connect.
     # Could be host, bridge or the name of a custom network.
     # If it's empty, act_runner will create a network automatically.
     network: ""
     # Whether to use privileged mode or not when launching task containers (privileged mode is required for Docker-in-Docker).
     privileged: false
     # And other options to be used when the container is started (eg, --add-host=my.gitea.url:host-gateway).
     options:
     # The parent directory of a job's working directory.
     # If it's empty, /workspace will be used.
     workdir_parent:

   ```
7. Создать директорию в любом месте (далее обозначается как actor)  
   В эту директорию поместить act-runner и config.yml

8. Дополнить файл docker-compose.yml для сервера Gitea:  
   ```yaml
   networks:
     giteanet:
       name: giteanet
       driver: bridge
   services:
     gitea:
       image: gitea/gitea:nightly
       container_name: gitea
       environment:
       - USER_UID=1000
       - USER_GID=1000
       restart: always
       networks:
       - giteanet
       volumes:
       - ./gitea:/data
       - /etc/timezone:/etc/timezone:ro
       - /etc/localtime:/etc/localtime:ro
       ports:
       - "3000:3000"
       - "222:22"
       stdin_open: true
       tty: true
     runner:
       image: ubuntu:latest
       container_name: runner
       networks:
         - giteanet
       depends_on:
         - gitea
       volumes:
         - /etc/ssl/certs:/etc/ssl/certs
         - /<actor>:/actor
         - /var/run/docker.sock:/var/run/docker.sock
       command:
         - /bin/sh
         - -c
         - |
           /actor/act_runner register --token <token> --instance http://gitea:3000 --name Runner --no-interactive --config /actor/config.yml
           /actor/act_runner daemon --config /actor/config.yml
   ```
   где:  
   `<token>` - взятый ранее token  
   `<actor>` - директория из предыдущего пункта  

9. В директории actor изменить config.yml следующим образом:
   - `runner`: `insecure`: `false` на `true`
   - `runner`: `file`: `.runner` на `/actor/.runner`
   - `container`: `network`: "" на `giteanet`
   - `container`: `options`: на `--add-host=my.gitea.url:host-gateway --network="host"`

    Как это должно выглядеть:
   ```yaml
    log:
     level: info
   
   runner:
     file: /actor/.runner
     insecure: true
     capacity: 1
     envs:
       A_TEST_ENV_NAME_1: a_test_env_value_1
       A_TEST_ENV_NAME_2: a_test_env_value_2
     env_file: .env
     timeout: 3h
     fetch_timeout: 5s
     fetch_interval: 2s
   
   cache:
     enabled: true
     dir: ""
     host: ""
     port: 0
   
   container:
     network: giteanet
     options: --add-host=my.gitea.url:host-gateway --network="host"
     privileged: false
     workdir_parent:

     ...
   ```
10. В директории с данными Gitea сервера в файле gitea/gitea/conf/app.ini изменить параметр
   ```ini
   [server]
   ROOT_URL=http://0.0.0.0:3000
   ```
   на название сервиса Gitea в docker-compose
   ```ini
   [server]
   ROOT_URL=http://gitea:3000
   ```

### Использование Gitea Actions:
Процесс использования очень схож с Github Actions
Файлы .yml должны находиться в репозитории в папке `.gitea/workflows`

Стандартный домен для импортируемых действий - gitea.com
`actions/checkout@v3 == https://gitea.com/actions/checkout@v3`

Его можно изменить через app.ini
```ini
[actions]
DEFAULT_ACTIONS_URL=https://gitea.com
```

Т.к. репозиторий gitea не имеет такого количества действий, как Github, в действиях также поддерживаются ссылки на действия и из Github, и из локальной версии gitea (только их домен будет тот же, что и ROOT_URL в app.ini)
Раннер "понимает" запись и без домена, и с доменом

>actions/checkout@v3; OK
>https://github.com/actions/download-artifact@v3; OK
>http://gitea:3000/user/repo@master; OK


Пример .yml для сборки документации Sphinx и её загрузки в виде артефакта:
```yaml
name: building Sphinx
run-name: ${{ gitea.actor }} is building Sphinx docs
on: [push]

jobs:
  buildDocs:
    runs-on: ubuntu-latest
    steps:
      - name: Check out the repository
        uses: actions/checkout@v3
      - name: Preparе working environment
        run: |
          apt-get -y update
          apt-get -y install zip pip
          pip install -r ${{ gitea.workspace }}/requirements.txt
      - name: Launch build script
        run: |
          sphinx-build -b html ./ _build/html
        shell: bash
      - name: Archive built docs
        run: cd _build && zip -r -5 irs_docs.zip html
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: irs_docs.zip
          path: _build/irs_docs.zip
 ```
- С пайплайнами удалённо работать нельзя, у Gitea пока нет API действий (1.20)
- Push без изменений запускает действия, которые триггерятся на push
- Вне зависимости от исхода отдельной работы или действия в целом, их можно перезапустить
- "Параллельный" запуск нескольких работ в одном действии возможен через [matrix](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)


## Использование вебхука для приёма файлов и в качестве хоста сайта

Требования:
Скачать приложение и его данные из репозитория:  
[полная версия(с тестами)](https://github.com/UnicPlay/webhook)  
[необходимый минимум](https://github.com/UnicPlay/webhook/releases/tag/v1-alpha)

Описание приложения:
Приложение на основе FastAPI, в нем четыре "ручки":
1. Приём сообщения о начале передачи данных
2. Приём сообщения, содержащего данные
3. Передача запрошенной страницы
4. Передача индексной страницы

Алгоритм работы с приложением:
0. Под "адресом" подразумевается IP-адрес и порт работающего сервера, после которого идёт искомый адрес (например адрес `/hello` с сервером, запущенным на 0.0.0.0:5000 подразумевает использование http://0.0.0.0:5000/hello)
В любой момент работы приложения можно отправить GET-запрос на адрес `/`и получить его индексную страницу
1. Для загрузки новых данных нужно:
   1. Отправить POST-запрос на адрес `/webhook/message/name`, содержащий заголовок `state`
   Вместо `name` подставить название директории для отправляемого файла
   2. Отправить POST-запрос на адрес `/webhook/download/name`, содержащий заголовок `Download` и загружаемый файл в формате .tar
   Файл будет автоматически распакован в папку name.
2. Для получения данных в браузере нужно ввести искомый адрес файла в подконтрольной приложению части файловой системы
Из-за специфики работы с раннером и автоматизации процесса, приложение обрабатывает адреса файлов типа `/dir/file.txt` как `/dir/html/file.txt`


Порядок действий для запуска вебхука:
1. Добавить в docker-compose новый сервис webhook:
```yaml
services:
  webhook:
     build:
       context: "/home/study5/dev/site"
     networks:
       - giteanet
     ports:
       - "8000:8000"
```
где:
`context` - путь до директории с Dockerfile

2. В .yml-файлы репозитория добавить отправку запроса и файлов  

Пример (обновлённые части выделены пустыми комментариями):
```yaml
name: building Sphinx
run-name: ${{ gitea.actor }} is building Sphinx docs
on: [push]

jobs:
  buildDocs:
    runs-on: ubuntu-latest
    steps:
      - name: Check out the branch
        uses: actions/checkout@v3
      - name: Prepare working environment
        run: |
          apt-get update
          apt-get install -qy curl pip
          pip install -r ${{ gitea.workspace }}/requirements.txt
####################################################################
      - name: Send a POST request to local webhook
        run: >
          BRANCH_NAME=$(echo ${GITHUB_REF#refs/heads/}) &&
          curl -X POST
          -H "State: starting"
          http://webhook:8000/webhook/message/${BRANCH_NAME}
        shell: bash
####################################################################
      - name: Launch build script
        run: |
          chmod +x build.sh
          ./build.sh
        shell: bash
      - name: Archive built docs
        run: >
          BRANCH_NAME=$(echo ${GITHUB_REF#refs/heads/}) &&
          cd _build && tar -cvf ${BRANCH_NAME}.tar html
      - name: Upload them as artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${BRANCH_NAME}.tar
          path: /_build/${BRANCH_NAME}.tar
#--------------------------------------------------------------------
      - name: Send them to webhook host
        run: >
          BRANCH_NAME=$(echo ${GITHUB_REF#refs/heads/}) &&
          curl -X POST
          -H "Download: true"
          -F "file=@_build/${BRANCH_NAME}.tar"
          http://webhook:8000/webhook/download/${BRANCH_NAME}
        shell: bash
##--------------------------------------------------------------------
```

Инструкция по запуску:
В директории с файлом docker-compose запустить терминал и ввести команду
`sudo docker-compose up -d --build`


